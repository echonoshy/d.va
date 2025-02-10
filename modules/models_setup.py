import argparse
import logging

from modules.core.models import zoo
from modules.devices import devices
from modules.core.models.zoo import model_zoo
from modules.utils import env

logger = logging.getLogger(__name__)


def setup_model_args(parser: argparse.ArgumentParser):
    parser.add_argument("--compile", action="store_true", help="Enable model compile")
    parser.add_argument(
        "--flash_attn", action="store_true", help="Enable flash attention"
    )
    parser.add_argument("--vllm", action="store_true", help="Enable vllm engine")
    parser.add_argument(
        "--no_half",
        action="store_true",
        help="Disalbe half precision for model inference",
    )
    parser.add_argument(
        "--off_tqdm",
        action="store_true",
        help="Disable tqdm progress bar",
    )
    parser.add_argument(
        "--device_id",
        type=str,
        help="Select the default CUDA device to use (export CUDA_VISIBLE_DEVICES=0,1,etc might be needed before)",
        default=None,
    )
    parser.add_argument(
        "--use_cpu",
        nargs="+",
        help="use CPU as torch device for specified modules",
        default=[],
        type=str.lower,
        choices=["all", "chattts", "enhancer", "trainer"],
    )
    # TODO: tts_pipeline 引入之后还不支持从这里配置
    parser.add_argument(
        "--lru_size",
        type=int,
        default=64,
        help="Set the size of the request cache pool, set it to 0 will disable lru_cache",
    )
    parser.add_argument(
        "--debug_generate",
        action="store_true",
        help="Enable debug mode for audio generation",
    )
    parser.add_argument(
        "--preload_models",
        action="store_true",
        help="Preload all models at startup",
    )


def process_model_args(args: argparse.Namespace):
    lru_size = env.get_and_update_env(args, "lru_size", 64, int)
    compile = env.get_and_update_env(args, "compile", False, bool)
    flash_attn = env.get_and_update_env(args, "flash_attn", False, bool)
    vllm = env.get_and_update_env(args, "vllm", False, bool)
    device_id = env.get_and_update_env(args, "device_id", None, str)
    use_cpu = env.get_and_update_env(args, "use_cpu", [], list)
    no_half = env.get_and_update_env(args, "no_half", False, bool)
    off_tqdm = env.get_and_update_env(args, "off_tqdm", False, bool)
    debug_generate = env.get_and_update_env(args, "debug_generate", False, bool)
    preload_models = env.get_and_update_env(args, "preload_models", False, bool)

    # TODO: 需要等 zoo 模块实现
    # generate_audio.setup_lru_cache()
    devices.reset_device()
    devices.first_time_calculation()

    if compile:
        logger.info("Model compile is enabled")

    if preload_models:
        """
        TODO: 增加配置加载其他模型，目前只会加载 chat_tts 和 resemble_enhance
        """
        logger.info("Preload models at startup, load...")

        model_zoo.get_chat_tts().load()
        model_zoo.get_resemble_enhance().load()

        logger.info("Preload models at startup, load done")
