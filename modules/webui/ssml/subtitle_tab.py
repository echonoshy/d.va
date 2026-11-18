import xml.dom.minidom

from modules.studio import forms as ui
import pysubs2

from modules.core.ssml.SSMLParser import SSMLBreak, SSMLSegment
from modules.webui import webui_utils


def read_subtitle_file_to_segs(file: str, spk: str):
    if spk != "*random" and ":" in spk:
        spk = spk.split(":")[-1].strip()

    subs = pysubs2.load(file, encoding="utf-8")
    ts = 0

    segs = []

    for line in subs:
        start = line.start
        end = line.end
        if start > ts:
            break_duration = start - ts
            break_duration = round(break_duration)
            segs.append(SSMLBreak(break_duration))

        duration = end - start
        if duration > 0:
            seg = SSMLSegment(text=line.text)
            if spk != "*random":
                seg.attrs.spk = spk
            seg.attrs.duration = f"{duration}ms"
            segs.append(seg)
        else:
            pass
        ts = end

    return segs


def read_subtitle_file(file: str, spk: str):
    if not file:
        raise ui.Error("Please upload a subtitle file")
    if spk != "*random" and ":" in spk:
        spk = spk.split(":")[-1].strip()

    subs = pysubs2.load(file, encoding="utf-8")

    ts = 0
    document = xml.dom.minidom.Document()

    root = document.createElement("speak")
    root.setAttribute("version", "0.1")

    document.appendChild(root)

    for line in subs:
        start = line.start
        end = line.end
        if start > ts:
            break_node = document.createElement("break")
            break_duration = start - ts
            break_duration = round(break_duration)
            if break_duration > 0:
                break_node.setAttribute("time", str(break_duration) + "ms")
                root.appendChild(break_node)
            else:
                # TODO: logging
                pass
        duration = end - start
        if duration > 0:
            voice_node = document.createElement("voice")
            voice_node.setAttribute("duration", str(duration) + "ms")
        else:
            continue
        if spk != "*random":
            voice_node.setAttribute("spk", spk)
        voice_node.appendChild(document.createTextNode(line.text))
        root.appendChild(voice_node)
        ts = end

    xml_content = document.toprettyxml(indent=" " * 2)
    return xml_content


# 读取字幕为表格，用于传递给 脚本 tab
def read_subtitle_to_table(file: str, spk: str):
    if not file:
        raise ui.Error("Please upload a subtitle file")

    segs = read_subtitle_file_to_segs(file, spk)
    data = []
    # table_headers = [
    #     "index",
    #     "type",
    #     "duration",
    #     "speed",
    #     "speaker",
    #     "text",
    #     "style",
    # ]
    index = 1
    for seg in segs:
        if isinstance(seg, SSMLSegment):
            data.append(
                [
                    index,
                    "voice",
                    seg.attrs.duration,
                    "",
                    seg.attrs.spk,
                    seg.text,
                    "",
                ]
            )
        elif isinstance(seg, SSMLBreak):
            duration = seg.attrs.duration
            data.append(
                [
                    index,
                    "break",
                    f"{duration}ms" if isinstance(duration, int) else duration,
                    "",
                    "",
                    "",
                    "",
                ]
            )
        else:
            raise ValueError(f"Unknown segment type: {type(seg)}")
        index += 1

    return data


# 输入字幕文件，转为 ssml 格式发送到 ssml
def create_subtitle_tab(
    ssml_input: ui.Textbox,
    tabs1: ui.Tabs,
    tabs2: ui.Tabs,
    script_table_out: ui.DataFrame,
):
    speakers, speaker_names = webui_utils.get_speaker_names()
    speaker_names = ["*random"] + speaker_names

    with ui.Row():
        with ui.Column(scale=1):
            with ui.Group():
                ui.Markdown("🗣️Speaker")
                spk_input_dropdown = ui.Dropdown(
                    choices=speaker_names,
                    interactive=True,
                    value="female : female2",
                    show_label=False,
                )

        with ui.Column(scale=2):
            file_upload = ui.File(label="Upload file", file_types=[".srt", ".ass", ".vtt"])

            send_ssml_btn = ui.Button("📩Send to SSML", variant="primary")
            send_script_btn = ui.Button("📩Send to Script")

        # with ui.Column(scale=3):
        #     text_input = ui.Textbox(label="Content")
        #     text_format = ui.Dropdown(
        #         choices=["txt", "srt", "vtt", "tsv", "json"],
        #         label="Format",
        #         value="srt",
        #     )

        #     send_text_btn = ui.Button(value="Send to SSML")

    send_ssml_btn.click(
        fn=read_subtitle_file,
        inputs=[file_upload, spk_input_dropdown],
        outputs=[ssml_input],
    )
    send_script_btn.click(
        fn=read_subtitle_to_table,
        inputs=[file_upload, spk_input_dropdown],
        outputs=[script_table_out],
    )

    def to_ssml_tab():
        return ui.Tabs(selected="ssml"), ui.Tabs(selected="ssml.editor")

    def to_script_tab():
        return ui.Tabs(selected="ssml"), ui.Tabs(selected="ssml.script")

    send_ssml_btn.click(to_ssml_tab, inputs=[], outputs=[tabs1, tabs2])
    send_script_btn.click(to_script_tab, inputs=[], outputs=[tabs1, tabs2])
