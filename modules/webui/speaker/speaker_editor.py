from modules.studio import forms as ui
import torch

from modules.core.spk.TTSSpeaker import TTSSpeaker
from modules.utils.hf import spaces
from modules.webui import webui_config
from modules.webui.webui_utils import SPK_FILE_EXTS, tts_generate


@torch.inference_mode()
@spaces.GPU(duration=120)
def test_spk_voice(
    spk_file,
    text: str,
    model: str,
    temperature: float,
    top_p: int,
    top_k: int,
    progress=None,
):
    if spk_file == "" or spk_file is None:
        return None
    spk = TTSSpeaker.from_file(spk_file)
    return tts_generate(
        spk=spk,
        text=text,
        model_id=model,
        temperature=temperature,
        top_k=top_k,
        top_p=top_p,
        progress=progress,
        eos="。",
    )


def speaker_editor_ui():
    def create_test_voice_card(
        spk_file,
        model_id_select,
        temperature_input,
        top_p_input,
        top_k_input,
    ):
        with ui.Group():
            ui.Markdown("🎤Test voice")
            with ui.Row():
                test_voice_btn = ui.Button("Test Voice", variant="secondary")

                with ui.Column(scale=4):
                    test_text = ui.Textbox(
                        label="Test Text",
                        placeholder="Please input test text",
                        value=webui_config.localization.DEFAULT_SPEAKER_TEST_TEXT,
                    )
                    with ui.Row():
                        with ui.Column(scale=4):
                            output_audio = ui.Audio(label="Output Audio", format="mp3")

        test_voice_btn.click(
            fn=test_spk_voice,
            inputs=[
                spk_file,
                test_text,
                model_id_select,
                temperature_input,
                top_p_input,
                top_k_input,
            ],
            outputs=[output_audio],
        )

        return test_voice_btn

    # 读取 spk 并 更新 info
    def load_spk_file_to_info(spk_file):
        if spk_file == "" or spk_file is None:
            return "None"
        spk = TTSSpeaker.from_file(spk_file)
        name = spk.name
        gender = spk.gender
        desc = spk.desc
        version = spk.version
        author = spk.author

        rows = [
            "💌 Speaker info",
            f"- Name: {name}",
            f"- Gender: {gender}",
            f"- Author: {author}",
            f"- Version: {version}",
            f"- Description: {desc}",
        ]
        return "\n".join(rows)

    # TODO 也许需要写个说明？
    # ui.Markdown("SPEAKER_CREATOR_GUIDE")

    with ui.Row():
        with ui.Column(scale=2):
            with ui.Group():
                ui.Markdown("💼Speaker file")
                spk_file = ui.File(label="*.json file", file_types=SPK_FILE_EXTS)
                spk_info = ui.Markdown("None")

                spk_file.change(
                    fn=load_spk_file_to_info,
                    inputs=spk_file,
                    outputs=spk_info,
                )

            with ui.Group():
                # 模型选择
                model_id_select = ui.Dropdown(label="Model", choices=["chat-tts", "fish-speech"], value="chat-tts")

            with ui.Group():
                # 采样率
                ui.Markdown("🎛️Sampling")
                temperature_input = ui.Slider(0.01, 2.0, value=0.3, step=0.01, label="Temperature")
                top_p_input = ui.Slider(0.1, 1.0, value=0.7, step=0.1, label="Top P")
                top_k_input = ui.Slider(1, 50, value=20, step=1, label="Top K")

        with ui.Column(scale=5):
            kwargs = dict(
                spk_file=spk_file,
                model_id_select=model_id_select,
                temperature_input=temperature_input,
                top_p_input=top_p_input,
                top_k_input=top_k_input,
            )

            create_test_voice_card(**kwargs)
            create_test_voice_card(**kwargs)
            create_test_voice_card(**kwargs)
            create_test_voice_card(**kwargs)
