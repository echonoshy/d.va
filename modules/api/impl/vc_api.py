from typing import Optional

from fastapi import Depends, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from modules.api import utils as api_utils
from modules.api.Api import APIManager
from modules.core.handler.datacls.audio_model import AudioFormat, EncoderConfig
from modules.core.handler.datacls.vc_model import VCConfig
from modules.core.handler.VCHandler import VCHandler
from modules.core.spk.TTSSpeaker import TTSSpeaker


class VoiceCloneForm(BaseModel):
    src_audio: UploadFile

    ref_audio: Optional[UploadFile]

    ref_spk: Optional[str]
    spk_emotion: Optional[str]

    model: str = "open-voice"

    tau: float = 0.3

    format: str = "mp3"

    @classmethod
    def as_form(
        cls,
        src_audio: UploadFile,
        ref_audio: Optional[UploadFile] = None,
        ref_spk: Optional[str] = None,
        spk_emotion: Optional[str] = None,
        model: str = "open-voice",
        tau: float = 0.3,
        format: str = "mp3",
    ):
        return cls(
            src_audio=src_audio,
            ref_audio=ref_audio,
            ref_spk=ref_spk,
            spk_emotion=spk_emotion,
            model=model,
            tau=tau,
            format=format,
        )


async def read_upload_file(file: UploadFile):
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from starlette.concurrency import run_in_threadpool
    from modules.studio.media import decode_media, read_mono

    with TemporaryDirectory() as directory:
        source = Path(directory) / "source"
        normalized = Path(directory) / "audio.wav"
        with source.open("wb") as stream:
            while chunk := await file.read(1024 * 1024):
                if stream.tell() + len(chunk) > 32 * 1024 ** 2:
                    raise HTTPException(413, "上传上限为 32 MiB")
                stream.write(chunk)
        try:
            await run_in_threadpool(decode_media, source, normalized)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return await run_in_threadpool(read_mono, normalized)


def setup(app: APIManager):
    @app.post(
        "/v1/vc",
        description="Voice cloning API",
        response_class=StreamingResponse,
        tags=["Voice Clone"],
    )
    async def voice_clone(request: Request, form: VoiceCloneForm = Depends(VoiceCloneForm.as_form)):
        model = form.model
        src_audio = form.src_audio
        ref_audio = form.ref_audio
        ref_spk = form.ref_spk
        spk_emotion = form.spk_emotion
        tau = form.tau
        format = form.format

        if ref_audio is None and ref_spk is None:
            raise HTTPException(status_code=422, detail="Either ref_audio or ref_spk should be provided")
        if src_audio is None:
            raise HTTPException(status_code=422, detail="src_audio should be provided")
        if format not in AudioFormat.__members__:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid format. Supported formats are {AudioFormat.__members__}",
            )

        src_audio_wav = await read_upload_file(src_audio)

        if ref_spk is not None:
            calc_params = api_utils.calc_spk_style(spk=ref_spk)

            ref_spk = calc_params.get("spk")
            if not isinstance(ref_spk, TTSSpeaker):
                raise HTTPException(status_code=422, detail="Invalid speaker")

        if ref_audio is not None:
            ref_audio_wav = await read_upload_file(ref_audio) if ref_audio is not None else None
            ref_spk = TTSSpeaker.from_ref_wav(ref_wav=ref_audio_wav)

        vc_config = VCConfig(enabled=True, mid=model, emotion=spk_emotion, tau=tau)
        encoder_config = EncoderConfig(
            format=AudioFormat(format),
            bitrate="64k",
        )

        try:
            handler = VCHandler(
                ref_spk=ref_spk,
                input_audio=src_audio_wav,
                vc_config=vc_config,
                encoder_config=encoder_config,
            )

            return handler.enqueue_to_response(request=request)
        except Exception as exc:
            import logging

            logging.exception(exc)

            if isinstance(exc, HTTPException):
                raise exc
            raise HTTPException(status_code=500, detail=str(exc))
