"""Decode local uploads with a verified container and a bounded PCM output."""

import os
import subprocess
from pathlib import Path

import soundfile as sf

MEDIA = {".wav", ".mp3", ".flac", ".aif", ".aiff", ".ogg", ".m4a", ".aac", ".opus", ".mp4", ".webm", ".mov", ".mkv"}
MAX_SECONDS = 15 * 60


def container(path):
    with Path(path).open("rb") as stream:
        head = stream.read(16)
    if head[:4] in (b"RIFF", b"RF64") and head[8:12] == b"WAVE":
        return "wav"
    if head[:4] == b"FORM" and head[8:12] in (b"AIFF", b"AIFC"):
        return "aiff"
    if head.startswith(b"ID3"):
        return "mp3"
    if len(head) >= 2 and head[0] == 255 and head[1] & 224 == 224:
        return "mp3" if head[1] & 6 else "aac"
    if head.startswith(b"OggS"):
        return "ogg"
    if head.startswith(b"fLaC"):
        return "flac"
    if head[4:8] == b"ftyp":
        return "mov"
    if head.startswith(bytes.fromhex("1a45dfa3")):
        return "matroska"
    raise ValueError("文件内容不是支持的音频或视频格式")


def decode_media(source, destination):
    result = subprocess.run(
        [
            os.environ.get("FFMPEG_PATH", "ffmpeg"),
            "-nostdin",
            "-loglevel",
            "error",
            "-protocol_whitelist",
            "file",
            "-f",
            container(source),
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-t",
            str(MAX_SECONDS + 1),
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            "-y",
            str(destination),
        ],
        capture_output=True,
        timeout=150,
    )
    if result.returncode:
        raise ValueError("读取音轨失败，请检查文件中是否含有可播放的声音")
    info = sf.info(destination)
    if not 0 < info.frames <= MAX_SECONDS * info.samplerate:
        raise ValueError("单个上传音轨最长为 15 分钟")


def read_mono(path):
    samples, rate = sf.read(path, dtype="int16", always_2d=True)
    return rate, samples.mean(axis=1).round().astype("int16")
