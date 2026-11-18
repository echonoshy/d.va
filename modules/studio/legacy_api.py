"""Standalone loopback API for 5518052 clients. Start with python -m modules.studio.legacy_api."""

import os
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware


def routes():
    from modules import config
    from modules.api.api_setup import create_api
    from fastapi.openapi.docs import get_swagger_ui_html

    app = FastAPI(title="D.Va model API", docs_url=None, redoc_url=None, root_path_in_servers=False)
    config.api = create_api(app, exclude=[p for p in os.getenv("EXCLUDE", "").split(",") if p])
    if os.getenv("NO_DOCS") != "1":

        @app.get("/docs", include_in_schema=False)
        def docs():
            return get_swagger_ui_html(openapi_url="/openapi.json", title=app.title)

    return app


def application():
    os.chdir(Path(__file__).resolve().parents[2])
    from modules.repos_static.sys_paths import setup_repos_paths

    setup_repos_paths()
    from modules.studio.device import configure

    configure()
    app = routes()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])

    @app.middleware("http")
    async def local_origin(req: Request, call_next):
        origin = req.headers.get("origin")
        if origin and urlsplit(origin).netloc != req.headers.get("host"):
            return JSONResponse({"detail": "Origin is not allowed"}, 403)
        return await call_next(req)

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(application(), host="127.0.0.1", port=int(os.getenv("DVA_API_PORT", "7860")))
