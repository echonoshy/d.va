import tempfile

from modules.studio import forms as ui
import torch

from modules.core.spk import TTSSpeaker, spk_mgr
from modules.utils.hf import spaces
from modules.webui import webui_config, webui_utils
from modules.webui.webui_utils import tts_generate


def spk_to_tensor(spk: str):
    spk = spk.split(" : ")[1].strip() if " : " in spk else spk
    if spk == "None" or spk == "":
        return None
    return spk_mgr.get_speaker(spk).get_token("chat-tts").tokens[0]


def get_speaker_show_name(spk: TTSSpeaker):
    if spk.gender == "*" or spk.gender == "":
        return spk.name
    return f"{spk.gender} : {spk.name}"


def merge_spk(
    spk_a: str,
    spk_a_w: float,
    spk_b: str,
    spk_b_w: float,
    spk_c: str,
    spk_c_w: float,
    spk_d: str,
    spk_d_w: float,
):
    tensor_a = spk_to_tensor(spk_a)
    tensor_b = spk_to_tensor(spk_b)
    tensor_c = spk_to_tensor(spk_c)
    tensor_d = spk_to_tensor(spk_d)

    if tensor_a is None and tensor_b is None and tensor_c is None and tensor_d is None:
        raise ui.Error("At least one speaker should be selected")

    merge_tensor = torch.zeros_like(tensor_a if tensor_a is not None else (tensor_b if tensor_b is not None else tensor_c if tensor_c is not None else tensor_d))

    total_weight = 0
    if tensor_a is not None:
        merge_tensor += spk_a_w * tensor_a
        total_weight += spk_a_w
    if tensor_b is not None:
        merge_tensor += spk_b_w * tensor_b
        total_weight += spk_b_w
    if tensor_c is not None:
        merge_tensor += spk_c_w * tensor_c
        total_weight += spk_c_w
    if tensor_d is not None:
        merge_tensor += spk_d_w * tensor_d
        total_weight += spk_d_w

    if total_weight <= 0:
        raise ui.Error("选中音色的权重之和必须大于零")
    merge_tensor /= total_weight

    merged_spk = TTSSpeaker.from_token(tokens=[merge_tensor], model_id="chat-tts")
    merged_spk.set_name("<MIX>")

    return merged_spk


@torch.inference_mode()
@spaces.GPU(duration=120)
def merge_and_test_spk_voice(
    spk_a,
    spk_a_w,
    spk_b,
    spk_b_w,
    spk_c,
    spk_c_w,
    spk_d,
    spk_d_w,
    test_text,
    progress=None,
):
    merged_spk = merge_spk(
        spk_a,
        spk_a_w,
        spk_b,
        spk_b_w,
        spk_c,
        spk_c_w,
        spk_d,
        spk_d_w,
    )
    return tts_generate(spk=merged_spk, text=test_text, progress=progress)


@torch.inference_mode()
@spaces.GPU(duration=120)
def merge_spk_to_file(
    spk_a,
    spk_a_w,
    spk_b,
    spk_b_w,
    spk_c,
    spk_c_w,
    spk_d,
    spk_d_w,
    speaker_name,
    speaker_gender,
    speaker_desc,
):
    merged_spk = merge_spk(spk_a, spk_a_w, spk_b, spk_b_w, spk_c, spk_c_w, spk_d, spk_d_w)
    merged_spk.set_name(speaker_name)
    merged_spk.set_gender(speaker_gender)
    merged_spk.set_desc(speaker_desc)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".spkv1.json") as tmp_file:
        tmp_file.write(merged_spk.to_json_str().encode("utf-8"))
        tmp_file_path = tmp_file.name

    return tmp_file_path


# 显示 a b c d 四个选择框，选择一个或多个，然后可以试音，并导出
def create_speaker_merger():
    def get_spk_choices():
        def is_chattts_spk(spk: TTSSpeaker):
            return spk.get_token("chat-tts") is not None

        speakers, speaker_names = webui_utils.get_speaker_names(is_chattts_spk)
        speaker_names = ["None"] + speaker_names
        return speaker_names

    ui.Markdown("SPEAKER_MERGER_GUIDE")

    def spk_picker(label_tail: str):
        with ui.Row():
            spk_a = ui.Dropdown(choices=get_spk_choices(), value="None", label=f"Speaker {label_tail}")
            refresh_a_btn = ui.Button("🔄", variant="secondary")

        def refresh_a():
            spk_mgr.refresh()
            speaker_names = get_spk_choices()
            return ui.update(choices=speaker_names)

        refresh_a_btn.click(refresh_a, outputs=[spk_a])
        spk_a_w = ui.Slider(
            value=1,
            minimum=0,
            maximum=10,
            step=0.1,
            label=f"Weight {label_tail}",
        )
        return spk_a, spk_a_w

    with ui.Row():
        with ui.Column(scale=5):
            with ui.Row():
                with ui.Group():
                    spk_a, spk_a_w = spk_picker("A")

                with ui.Group():
                    spk_b, spk_b_w = spk_picker("B")

                with ui.Group():
                    spk_c, spk_c_w = spk_picker("C")

                with ui.Group():
                    spk_d, spk_d_w = spk_picker("D")

            with ui.Row():
                with ui.Column(scale=3):
                    with ui.Group():
                        ui.Markdown("🎤Test voice")
                        with ui.Row():
                            test_voice_btn = ui.Button("Test Voice", variant="secondary")

                            with ui.Column(scale=4):
                                test_text = ui.Textbox(
                                    label="Test Text",
                                    placeholder="Please input test text",
                                    value=webui_config.localization.DEFAULT_SPEAKER_MERAGE_TEXT,
                                )

                                output_audio = ui.Audio(label="Output Audio", format="mp3")

        with ui.Column(scale=1):
            with ui.Group():
                ui.Markdown("🗃️Save to file")

                speaker_name = ui.Textbox(label="Name", value="forge_speaker_merged")
                speaker_gender = ui.Textbox(label="Gender", value="*")
                speaker_desc = ui.Textbox(label="Description", value="merged speaker")

                save_btn = ui.Button("Save Speaker", variant="primary")

                merged_spker = ui.File(label="Merged Speaker", interactive=False, type="binary")

    test_voice_btn.click(
        merge_and_test_spk_voice,
        inputs=[
            spk_a,
            spk_a_w,
            spk_b,
            spk_b_w,
            spk_c,
            spk_c_w,
            spk_d,
            spk_d_w,
            test_text,
        ],
        outputs=[output_audio],
    )

    save_btn.click(
        merge_spk_to_file,
        inputs=[
            spk_a,
            spk_a_w,
            spk_b,
            spk_b_w,
            spk_c,
            spk_c_w,
            spk_d,
            spk_d_w,
            speaker_name,
            speaker_gender,
            speaker_desc,
        ],
        outputs=[merged_spker],
    )
