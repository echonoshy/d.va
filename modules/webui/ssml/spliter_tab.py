from modules.studio import forms as ui
import pandas as pd
import torch

from modules.webui import webui_utils
from modules.webui.webui_utils import get_styles, split_long_text


def merge_dataframe_to_ssml(dataframe, spk, style, seed=None):
    if style == "*auto":
        style = None
    if spk == "-1" or spk == -1:
        spk = None
    if seed == -1 or seed == "-1":
        seed = None

    from xml.etree import ElementTree as ET
    root = ET.Element("speak", version="0.1")
    for _, row in dataframe.iterrows():
        text = str(row.iloc[1]).strip()
        if text:
            attrs = {k: str(v) for k, v in (("spk", spk), ("style", style), ("seed", seed)) if v is not None}
            ET.SubElement(root, "voice", attrs).text = text
    return dataframe, spk, style, ET.tostring(root, encoding="unicode")


# 转换为 script tab 下面的 data 列表格式
def transfer_to_script_data(dataframe: pd.DataFrame, spk, style):
    script_data = []
    # table_headers = [
    #     "index",
    #     "type",
    #     "duration",
    #     "speed",
    #     "speaker",
    #     "text",
    #     "style",
    # ]
    for i, row in dataframe.iterrows():
        script_data.append(
            # {
            #     "index": i,
            #     "type": "voice",
            #     "text": row.iloc[1],
            #     "speaker": spk or "",
            #     "style": style or "",
            #     "duration": "",
            #     "speed": "",
            # }
            [
                i,
                "voice",
                "",
                "",
                spk or "",
                row.iloc[1],
                style or "",
            ]
        )
    return script_data, ui.Tabs(selected="ssml"), ui.Tabs(selected="ssml.script")


# 长文本处理
# 可以输入长文本，并选择切割方法，切割之后可以将拼接的SSML发送到SSML tab
# 根据 。 句号切割，切割之后显示到 data table
def create_spliter_tab(ssml_input, tabs1, tabs2, script_table_out):
    speakers, speaker_names = webui_utils.get_speaker_names()
    speaker_names = ["*random"] + speaker_names

    styles = ["*auto"] + [s.get("name") for s in get_styles()]

    with ui.Row():
        with ui.Column(scale=1):
            # 选择说话人 选择风格 选择seed
            with ui.Group():
                ui.Markdown("🗣️Speaker")
                spk_input_text = ui.Textbox(
                    label="Speaker (Text or Seed)",
                    value="female2",
                    show_label=False,
                )
                spk_input_dropdown = ui.Dropdown(
                    choices=speaker_names,
                    interactive=True,
                    value="female : female2",
                    show_label=False,
                )
                spk_rand_button = ui.Button(
                    value="🎲",
                    variant="secondary",
                )
            with ui.Group():
                ui.Markdown("🎭Style")
                style_input_dropdown = ui.Dropdown(
                    choices=styles,
                    interactive=True,
                    show_label=False,
                    value="*auto",
                )

            with ui.Group():
                ui.Markdown("🎛️Spliter")
                eos_input = ui.Textbox(
                    label="eos",
                    value="[uv_break]",
                )
                spliter_thr_input = ui.Slider(
                    label="Spliter Threshold",
                    value=100,
                    minimum=50,
                    maximum=1000,
                    step=1,
                )

        with ui.Column(scale=3):
            with ui.Group():
                ui.Markdown("📝Long Text Input")
                ui.Markdown("SSML_SPLITER_GUIDE")
                long_text_input = ui.Textbox(
                    label="Long Text Input",
                    lines=10,
                    placeholder="输入长文本",
                    elem_id="long-text-input",
                    show_label=False,
                )
                long_text_split_button = ui.Button("🔪Split Text")

            with ui.Group():
                ui.Markdown("🎨Output")
                long_text_output = ui.DataFrame(
                    headers=["index", "text", "length"],
                    datatype=["number", "str", "number"],
                    elem_id="long-text-output",
                    interactive=True,
                    wrap=True,
                    value=[],
                    row_count=(0, "dynamic"),
                    col_count=(3, "fixed"),
                )

                send_btn = ui.Button("📩Send to SSML", variant="primary")
                send_script_btn = ui.Button("📩Send to Script")

    spk_input_dropdown.change(
        fn=lambda x: x.startswith("*") and "-1" or x.split(":")[-1].strip(),
        inputs=[spk_input_dropdown],
        outputs=[spk_input_text],
    )
    spk_rand_button.click(
        lambda x: int(torch.randint(0, 2**32 - 1, (1,)).item()),
        inputs=[spk_input_text],
        outputs=[spk_input_text],
    )
    long_text_split_button.click(
        split_long_text,
        inputs=[
            long_text_input,
            spliter_thr_input,
            eos_input,
        ],
        outputs=[
            long_text_output,
        ],
    )

    send_btn.click(
        merge_dataframe_to_ssml,
        inputs=[
            long_text_output,
            spk_input_text,
            style_input_dropdown,
        ],
        outputs=[
            long_text_output,
            spk_input_text,
            style_input_dropdown,
            ssml_input,
        ],
    )

    def change_tab():
        return ui.Tabs(selected="ssml"), ui.Tabs(selected="ssml.editor")

    send_btn.click(change_tab, inputs=[], outputs=[tabs1, tabs2])

    send_script_btn.click(
        transfer_to_script_data,
        inputs=[long_text_output, spk_input_text, style_input_dropdown],
        outputs=[script_table_out, tabs1, tabs2],
    )
