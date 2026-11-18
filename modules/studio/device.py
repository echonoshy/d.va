"""Choose a common device for the text encoder, vocoder and training tensors."""

import os
import sys


def configure():
    import torch
    from modules import config
    from modules.devices import devices

    # The original ChatTTS encoder mixes CPU and MPS tensors on Apple Silicon.
    default = "cpu" if sys.platform == "darwin" or not torch.cuda.is_available() else "auto"
    requested = os.getenv("DVA_DEVICE", default)
    for option in ("compile", "flash_attn", "vllm", "off_tqdm", "debug_generate"):
        config.runtime_env_vars[option] = os.getenv(option.upper(), "").lower() in ("true", "1")
    config.runtime_env_vars.device_id = os.getenv("DEVICE_ID")
    config.runtime_env_vars.use_cpu = ["all"] if requested == "cpu" else os.getenv("USE_CPU", "").split(",")
    config.runtime_env_vars.no_half = requested == "cpu" or not torch.cuda.is_available() or os.getenv("NO_HALF") == "1"
    if requested == "cpu":
        torch.set_num_threads(min(4, os.cpu_count() or 1))
    devices.reset_device()
