from modules.studio import forms as ui

from modules.core.handler.datacls.audio_model import AdjustConfig
from modules.core.handler.datacls.enhancer_model import EnhancerConfig
from modules.core.pipeline.dcls import TTSPipelineContext
from modules.core.pipeline.factory import PipelineFactory
from modules.utils import audio_utils


def create_post_processor():
    # 编辑音频文件
    with ui.Row():
        with ui.Column(scale=1):
            with ui.Group():
                ui.Markdown("🎛️Adjuster")
                speed_input = ui.Slider(
                    label="Speed",
                    value=1.0,
                    minimum=0.5,
                    maximum=2.0,
                    step=0.1,
                )
                pitch_input = ui.Slider(
                    label="Pitch",
                    value=0,
                    minimum=-12,
                    maximum=12,
                    step=0.1,
                )
                volume_up_input = ui.Slider(
                    label="Volume Gain",
                    value=0,
                    minimum=-20,
                    maximum=6,
                    step=0.1,
                )

                enable_loudness_normalization = ui.Checkbox(
                    value=True,
                    label="Enable Loudness EQ",
                )
                headroom_input = ui.Slider(
                    label="Headroom",
                    value=1,
                    minimum=0,
                    maximum=12,
                    step=0.1,
                )

            with ui.Group():
                ui.Markdown("💪🏼Enhance")
                enable_enhance = ui.Checkbox(value=False, label="Enable Enhance")
                enable_de_noise = ui.Checkbox(value=False, label="Enable De-noise")

        with ui.Column(scale=3):
            input_audio = ui.Audio(label="原始音频文件")

            gen_button = ui.Button(
                "Generate",
                variant="primary",
                elem_classes="big-button",
            )

    with ui.Row():
        output_audio = ui.Audio(label="编辑后音频文件")

    def gen_audio(
        audio,
        speed,
        pitch,
        volume_up,
        enable_loudness_normalization,
        headroom,
        enable_enhance,
        enable_de_noise,
    ):
        if audio is None:
            raise ui.Error("Audio file is required.")

        pipeline = PipelineFactory.create_postprocess_pipeline(
            audio=audio,
            ctx=TTSPipelineContext(
                adjust_config=AdjustConfig(
                    pitch=pitch,
                    speed_rate=speed,
                    volume_gain_db=volume_up,
                    normalize=enable_loudness_normalization,
                    headroom=headroom,
                ),
                enhancer_config=EnhancerConfig(
                    enabled=enable_de_noise or enable_enhance or False,
                    lambd=0.9 if enable_de_noise else 0.1,
                ),
            ),
        )
        sr, audio_data = pipeline.generate()
        audio_data = audio_utils.audio_to_int16(audio_data)
        return sr, audio_data

    gen_button.click(
        fn=gen_audio,
        inputs=[
            input_audio,
            speed_input,
            pitch_input,
            volume_up_input,
            enable_loudness_normalization,
            headroom_input,
            enable_enhance,
            enable_de_noise,
        ],
        outputs=output_audio,
    )
