import logging
from pathlib import Path
from typing import Tuple

import numpy as np

from modules.core.models.tts.FireRed.FireRedInfer import (
    FireRedTTSInfer,
    FireRedTTSParams,
)
from modules.core.models.TTSModel import TTSModel
from modules.core.pipeline.dcls import TTSPipelineContext
from modules.core.pipeline.pipeline import TTSSegment
from modules.core.pipeline.processor import NP_AUDIO
from modules.devices import devices
from modules.utils.SeedContext import SeedContext

logger = logging.getLogger(__name__)


class FireRedTTSModel(TTSModel):
    model_id = "fire-red-tts"

    def __init__(self) -> None:
        super().__init__(FireRedTTSModel.model_id)

        self.fire_red: FireRedTTSInfer = None
        self.device = devices.get_device_for("fire-red-tts")

    def is_downloaded(self) -> bool:
        return Path("models/FireRedTTS").exists()

    def load(self):
        if self.fire_red:
            return self.fire_red
        logger.info("loadding FireRedTTS...")
        self.fire_red = FireRedTTSInfer(
            config_path="./modules/repos_static/FireRedTTS/config_24k.json",
            pretrained_path="./models/FireRedTTS",
            device=self.device,
        )
        logger.info("FireRedTTS model loaded.")
        return self.fire_red

    def unload(self) -> None:
        if self.fire_red is None:
            return
        self.fire_red.unload_models()
        self.fire_red = None
        devices.torch_gc()
        logger.info("FireRedTTS model unloaded.")

    def get_sample_rate(self):
        return 24000

    def generate(self, segment: TTSSegment, context: TTSPipelineContext) -> Tuple[NP_AUDIO]:
        model = self.load()

        seg0 = segment
        spk_wav, txt_smp = self.get_ref_wav(seg0)

        with SeedContext(seed=seg0.infer_seed):
            syn_audio = model.synthesize(
                audio=spk_wav,
                audio_sr=self.get_sample_rate(),
                text=seg0.text,
                # lang="auto",
                params=FireRedTTSParams(
                    top_p=seg0.top_p,
                    top_k=seg0.top_k,
                    temperature=seg0.temperature,
                ),
            )

        wav: np.ndarray = syn_audio.float().cpu().squeeze().numpy()

        return self.get_sample_rate(), wav

    def generate_batch(self, segments: list[TTSSegment], context: TTSPipelineContext) -> list[Tuple[NP_AUDIO]]:
        # NOTE: 原生不支持 batch 所以，就是简单的循环

        ret = []
        for seg in segments:
            ret.append(self.generate(segment=seg, context=context))

        return ret
