"""Start the TypeScript + React studio using the original Python entry point."""

import argparse
import os
from pathlib import Path
import sys

from dotenv import load_dotenv


def main():
    os.chdir(Path(__file__).resolve().parent)
    load_dotenv(os.getenv("ENV_FILE", ".env.webui"))
    load_dotenv(".env")
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("server_name", "language", "auth", "device_id", "exclude"):
        parser.add_argument("--" + flag)
    for flag in ("server_port", "tts_max_len", "ssml_max_len", "max_batch_size", "lru_size"):
        parser.add_argument("--" + flag, type=int)
    for flag in ("api", "webui_experimental", "debug", "no_half", "compile", "flash_attn", "vllm", "off_tqdm", "debug_generate", "preload_models", "no_docs", "off_track_tqdm"):
        parser.add_argument("--" + flag, action="store_true", default=None)
    parser.add_argument("--use_cpu", nargs="+")
    args = parser.parse_args()
    names = {"server_port": "PORT", "server_name": "HOST", "api": "DVA_ENABLE_API", "language": "DVA_LANGUAGE", "auth": "DVA_AUTH"}
    for key, value in vars(args).items():
        if value is not None:
            os.environ[names.get(key, key.upper())] = "1" if value is True else ",".join(value) if isinstance(value, list) else str(value)
    os.environ.setdefault("PORT", os.getenv("SERVER_PORT", "7860"))
    os.environ.setdefault("HOST", os.getenv("SERVER_NAME", "127.0.0.1"))
    os.environ.setdefault("DVA_PYTHON", sys.executable)
    os.execlp("node", "node", "--env-file-if-exists=.env", "server/index.mjs")


if __name__ == "__main__":
    main()
