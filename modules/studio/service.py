"""Loopback worker for the React form contract and the existing Python model handlers."""

import atexit
import json
import logging
import math
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from modules.studio.forms import Widget
from modules.studio.media import MEDIA, decode_media, read_mono

ROOT = Path(__file__).resolve().parents[2]
LIMIT = 32 * 1024 * 1024
WORK = tempfile.TemporaryDirectory(prefix="dva-studio-")
# Keep callback-generated files in the same private tree as exported downloads.
tempfile.tempdir = WORK.name
atexit.register(WORK.cleanup)
sessions = {}
guard = threading.RLock()
inference = threading.Lock()
form = None


def initialize():
    global form
    from modules.repos_static.sys_paths import setup_repos_paths

    setup_repos_paths()
    from modules.studio.device import configure

    configure()
    from modules.webui.app import create_interface

    form = create_interface()
    if os.getenv("PRELOAD_MODELS") == "1":
        from modules.core.models.zoo import model_zoo

        model_zoo.get_chat_tts().load()
        model_zoo.get_resemble_enhance().load()


class Session:
    def __init__(self):
        self.token = secrets.token_urlsafe(24)
        self.dir = Path(WORK.name) / self.token
        self.dir.mkdir()
        self.files = {}
        self.audio = {}
        self.state = {}
        self.last = time.monotonic()
        self.lock = threading.RLock()
        self.size = 0

    def register(self, path, name):
        size = path.stat().st_size
        if size > 128 * 1024**2 or self.size + size > 512 * 1024**2:
            path.unlink(missing_ok=True)
            raise ValueError("本次工作区音频已满，请刷新并重新开始。")
        self.size += size
        key = secrets.token_urlsafe(18)
        self.files[key] = (path, name)
        return {"file": key, "name": name, "url": f"/api/studio/files/{self.token}/{key}"}

    def save_result(self, val, kind, props):
        if val is None:
            return None
        if isinstance(val, (str, Path)):
            path = Path(val).resolve(strict=True)
            if not path.is_relative_to(Path(WORK.name).resolve()):
                raise ValueError("输出文件不在本次工作目录中")
            suffix = ".spkv1.json" if path.name.endswith(".spkv1.json") else path.suffix
            dest = self.dir / (secrets.token_hex(12) + suffix)
            shutil.move(path, dest)
            return self.register(dest, "D.Va" + suffix)
        import soundfile as sf

        sr, samples = val
        ext = "mp3" if props.get("format") == "mp3" else "wav"
        dest = self.dir / (secrets.token_hex(12) + "." + ext)
        sf.write(dest, samples, int(sr), format=ext)
        return self.register(dest, "D.Va." + ext)


def session_for(key):
    with guard:
        session = sessions.get(key)
        if not session:
            raise HTTPException(410, "页面已过期，请重新打开工作台")
        session.last = time.monotonic()
        return session


def fresh():
    with guard:
        for key, s in list(sessions.items()):
            if time.monotonic() - s.last > 3600 and s.lock.acquire(blocking=False):
                try:
                    shutil.rmtree(s.dir, ignore_errors=True)
                    del sessions[key]
                finally:
                    s.lock.release()
        if len(sessions) >= 64:
            raise HTTPException(429, "已打开过多工作区")
        s = Session()
        sessions[s.token] = s
        return s


def decode(node, value, s):
    k = node.kind
    if k == "State":
        return s.state.get(node.id, node.props.get("value"))
    if k in ("Audio", "File", "Video"):
        if value is None:
            return None
        if not isinstance(value, dict) or value.get("file") not in s.files:
            raise ValueError("请重新选择上传文件")
        path, _ = s.files[value["file"]]
        if k in ("Audio", "Video"):
            normalized = s.audio.get(value["file"])
            if normalized is None:
                raise ValueError("请选择包含音轨的文件")
            return str(normalized) if k == "Video" or node.props.get("type") == "filepath" else read_mono(normalized)
        allowed = [suffix for suffix in node.props.get("file_types", []) if suffix]
        if allowed and path.suffix not in allowed:
            raise ValueError("此文件与该输入框要求的格式不符")
        return str(path)
    if k == "DataFrame":
        import pandas as pd

        if not isinstance(value, list) or len(value) > 2000:
            raise ValueError("表格行数超过限制")
        return pd.DataFrame(value, columns=node.props["headers"]).fillna("")
    if k in ("Slider", "Number"):
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError("参数需要有效数字")
        if not node.props.get("minimum", -math.inf) <= value <= node.props.get("maximum", math.inf):
            raise ValueError("参数超出范围")
    if k == "Checkbox" and not isinstance(value, bool):
        raise ValueError("复选框值无效")
    if k not in ("Slider", "Number", "Checkbox") and value is not None and not isinstance(value, str):
        raise ValueError("文本参数格式有误")
    return value


def invoke(session, event_id, values):
    if not 0 <= event_id < len(form.events):
        raise ValueError("未知操作")
    event = form.events[event_id]
    if len(values) != len(event.inputs):
        raise ValueError("表单参数数目有误")
    with session.lock, inference:
        args = [decode(n, v, session) for n, v in zip(event.inputs, values)]
        result = event.fn(*args)
        if not event.outputs:
            return {}
        outputs = [result] if len(event.outputs) == 1 else result
        if len(outputs) != len(event.outputs):
            raise RuntimeError("回调返回的字段数目不一致")
        changes = {}
        for node, val in zip(event.outputs, outputs):
            if node.kind == "State":
                session.state[node.id] = val
                continue
            if isinstance(val, Widget):
                props = val.props
            elif node.kind in ("Audio", "File", "Video"):
                props = {"value": session.save_result(val, node.kind, node.props)}
            elif node.kind == "DataFrame" and hasattr(val, "to_numpy"):
                props = {"value": val.reindex(columns=node.props["headers"]).fillna("").to_numpy().tolist()}
            else:
                props = {"value": val}
            changes[node.id] = props
        return changes


def create_app():
    @asynccontextmanager
    async def lifespan(app):
        await run_in_threadpool(initialize)
        if os.getenv("DVA_ENABLE_API") == "1":
            from modules.studio.legacy_api import routes

            app.mount("/legacy", routes())
        yield

    app = FastAPI(lifespan=lifespan, docs_url=None, openapi_url=None, redoc_url=None)
    secret = os.environ["DVA_WORKER_TOKEN"]

    @app.middleware("http")
    async def authenticate(req, call_next):
        if not secrets.compare_digest(req.headers.get("x-dva-worker", ""), secret):
            return JSONResponse({"error": "Forbidden"}, status_code=403)
        return await call_next(req)

    @app.exception_handler(Exception)
    async def handle_error(req, exc):
        logging.exception("Studio operation failed")
        return JSONResponse({"error": str(exc)[:550] or type(exc).__name__}, status_code=422)

    @app.get("/schema")
    def schema():
        s = fresh()
        language = "en" if os.getenv("DVA_LANGUAGE") == "en" else "zh-CN"
        return {**form.schema(), "session": s.token, "labels": json.loads((ROOT / "language" / (language + ".json")).read_text())}

    @app.post("/run/{sid}/{event}")
    async def run(sid: str, event: int, req: Request):
        body = await req.json()
        return await run_in_threadpool(invoke, session_for(sid), event, body["values"])

    @app.post("/upload/{sid}")
    async def upload(sid: str, req: Request):
        s = session_for(sid)
        name = Path(req.query_params.get("name", "")).name
        ext = ".spkv1.json" if name.lower().endswith(".json") else Path(name).suffix.lower()
        if ext not in MEDIA | {".spkv1.json", ".srt", ".ass", ".vtt"}:
            raise HTTPException(415, "此文件类型不受支持")
        path = s.dir / (secrets.token_hex(12) + ext)
        normalized = s.dir / (secrets.token_hex(12) + ".wav")
        size = 0
        try:
            with path.open("xb") as out:
                async for chunk in req.stream():
                    size += len(chunk)
                    if size > LIMIT:
                        raise HTTPException(413, "上传上限为 32 MiB")
                    out.write(chunk)
            if not size:
                raise ValueError("所选文件为空")
            if ext in MEDIA:
                await run_in_threadpool(decode_media, path, normalized)
            with s.lock:
                extra = normalized.stat().st_size if normalized.exists() else 0
                s.size += extra
                try:
                    resource = s.register(path, name)
                except BaseException:
                    s.size -= extra
                    raise
                if extra:
                    s.audio[resource["file"]] = normalized
                return resource
        except BaseException:
            path.unlink(missing_ok=True)
            normalized.unlink(missing_ok=True)
            raise

    @app.get("/files/{sid}/{file}")
    def download(sid: str, file: str):
        s = session_for(sid)
        if file not in s.files:
            raise HTTPException(404)
        path, name = s.files[file]
        return FileResponse(path, filename=name, media_type="application/json" if path.suffix == ".json" else None)

    @app.get("/speakers/{sid}")
    def installed(sid: str):
        from modules.core.spk import spk_mgr

        session_for(sid)
        return {s.id: s.version or "" for s in spk_mgr.list_speakers()}

    @app.post("/speakers/{sid}")
    async def install_card(sid: str, req: Request):
        from modules.core.spk import TTSSpeaker, spk_mgr

        session_for(sid)
        data = await req.json()
        spk = TTSSpeaker.from_json(data)
        if not spk.name or not spk.id or not isinstance(spk.id, str):
            raise ValueError("音色卡缺少名称或 ID")
        import hashlib

        folder = ROOT / "data/speakers" / "imported"
        folder.mkdir(exist_ok=True)
        path = folder / (hashlib.sha256(spk.id.encode()).hexdigest() + ".spkv1.json")
        with inference:
            with tempfile.NamedTemporaryFile(dir=folder, delete=False) as tmp:
                tmp.write(spk.to_json_str().encode())
            os.replace(tmp.name, path)
            spk_mgr.refresh()
        return {"name": spk.name, "id": spk.id, "version": spk.version or ""}

    return app


if __name__ == "__main__":
    import uvicorn

    os.chdir(ROOT)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(64)
    # Node waits for uvicorn readiness before relaying the first request.
    port = sock.getsockname()[1]
    app = create_app()

    async def ready():
        print("DVA_READY " + str(port), flush=True)

    original = app.router.lifespan_context

    @asynccontextmanager
    async def boot(app):
        async with original(app):
            await ready()
            yield

    app.router.lifespan_context = boot
    uvicorn.Server(uvicorn.Config(app, access_log=False, log_level="warning")).run(sockets=[sock])
