from modules.studio import forms as ui

from modules.core.models.zoo import ModelZoo
from modules.webui import webui_config
from modules.webui.webui_utils import synthesize_ssml


def create_ssml_interface():
    with ui.Row():
        with ui.Column(scale=1):
            with ui.Group():
                ui.Markdown("🎛️Parameters")
                # batch size
                batch_size_input = ui.Slider(
                    label="Batch Size",
                    value=4,
                    minimum=1,
                    maximum=webui_config.max_batch_size,
                    step=1,
                )
                models = [ModelZoo.model_zoo.get_model(mid) for mid in ModelZoo.model_zoo.get_tts_model_ids()]
                # 选择模型
                selected_model = ui.Dropdown(
                    label="Model",
                    choices=[model.model_id for model in models],
                    value=models[0].model_id if len(models) > 0 else None,
                )

            with ui.Group():
                ui.Markdown("🎛️Spliter")
                eos_input = ui.Textbox(
                    label="eos",
                    value="。",
                )
                spliter_thr_input = ui.Slider(
                    label="Spliter Threshold",
                    value=100,
                    minimum=50,
                    maximum=1000,
                    step=1,
                )

            with ui.Group():
                ui.Markdown("🎛️Adjuster")
                # 调节 speed pitch volume
                # 可以选择开启 响度均衡

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
                    minimum=-12,
                    maximum=12,
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
                enable_enhance = ui.Checkbox(value=True, label="Enable Enhance")
                enable_de_noise = ui.Checkbox(value=False, label="Enable De-noise")

        with ui.Column(scale=3):
            with ui.Group():
                ui.Markdown("📝SSML Input")
                ui.Markdown("SSML_TEXT_GUIDE")
                ssml_input = ui.Textbox(
                    label="SSML Input",
                    lines=10,
                    value=webui_config.localization.DEFAULT_SSML_TEXT,
                    placeholder="输入 SSML 或选择示例",
                    elem_id="ssml_input",
                    show_label=False,
                )
                ssml_button = ui.Button("🔊Synthesize SSML", variant="primary")

            with ui.Group():
                ui.Markdown("🎄Examples")
                ui.Examples(
                    examples=webui_config.localization.ssml_examples,
                    inputs=[ssml_input],
                )

            with ui.Group():
                ui.Markdown("🎨Output")
                ssml_output = ui.Audio(label="Generated Audio", format="mp3")

    ssml_button.click(
        synthesize_ssml,
        inputs=[
            ssml_input,
            batch_size_input,
            enable_enhance,
            enable_de_noise,
            eos_input,
            spliter_thr_input,
            pitch_input,
            speed_input,
            volume_up_input,
            enable_loudness_normalization,
            headroom_input,
            selected_model,
        ],
        outputs=ssml_output,
    )

    return ssml_input
