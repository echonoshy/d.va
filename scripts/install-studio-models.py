"""Download the original inference weights into models/, checking each pinned object."""

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FILES = json.loads((ROOT / "scripts/studio-models.json").read_text())


def verified(path, spec):
    if not path.is_file() or path.stat().st_size != spec["size"]:
        return False
    digest = hashlib.sha256() if spec["sha256"] else hashlib.sha1(f"blob {spec['size']}\0".encode())
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == (spec["sha256"] or spec["git_blob"])


def install(spec):
    path = ROOT / "models" / spec["file"]
    if verified(path, spec):
        return
    if path.exists():
        raise ValueError(f"Existing file differs from the pinned model: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        stage = Path(tmp.name)
    try:
        subprocess.run(
            ["curl", "--fail", "--silent", "--show-error", "--location", "--retry", "2", "--connect-timeout", "15", "--speed-time", "60", "--speed-limit", "1024", "--output", str(stage), spec["url"]],
            check=True,
        )
        if not verified(stage, spec):
            raise ValueError(f"Checksum or size mismatch: {spec['file']}")
        os.replace(stage, path)
        print(spec["file"], flush=True)
    finally:
        stage.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("groups", nargs="*", help="ChatTTS, fish-speech-1_4, OpenVoiceV2, resemble-enhance (all by default)")
    groups = parser.parse_args().groups
    if set(groups) - {s["file"].split("/")[0] for s in FILES}:
        parser.error("Unknown model group")
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(install, [s for s in FILES if not groups or s["file"].split("/")[0] in groups]))
