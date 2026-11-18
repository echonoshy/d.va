from modules.studio import forms as ui
import pandas as pd
import xml.dom.minidom


def merge_dataframe_to_ssml(df: pd.DataFrame):
    document = xml.dom.minidom.Document()

    root = document.createElement("speak")
    root.setAttribute("version", "0.1")

    document.appendChild(root)

    for _, row in df.iterrows():
        text = row.get("text")
        spk = row.get("speaker")
        style = row.get("style")
        _type = row.get("type")
        duration = row.get("duration")
        speed = row.get("speed")

        if _type == "break":
            # add break node
            break_node = document.createElement("break")
            if duration:
                break_node.setAttribute("time", duration)
            root.appendChild(break_node)
            continue

        # NOTE: 感觉好像不需要 normalize
        # text = webui_utils.text_normalize(text)

        if text.strip() == "":
            continue

        voice_node = document.createElement("voice")
        if spk:
            voice_node.setAttribute("spk", spk)
        if style and style != "*auto":
            voice_node.setAttribute("style", style)

        # duration 和 speed 二选一
        if duration:
            voice_node.setAttribute("duration", duration)
        elif speed:
            voice_node.setAttribute("rate", speed)

        voice_node.appendChild(document.createTextNode(text))
        root.appendChild(voice_node)

    xml_content = document.toprettyxml(indent="  ")
    return xml_content


# fmt: off
script_default_value = [
    [1, "voice", "", "", "Bob", "Hello World", ""],
    [2, "voice", "", "", "Alice", "I am Alice. How are you?", ""],
    [3, "voice", "", "", "Bob", "I am Bob. I am learning how to use the SSML module.", ""]
]
# fmt: on


# 脚本页面，纯脚本列表，用于编辑
def create_script_tab(ssml_input, tabs1, tabs2):
    table_headers = [
        "index",
        "type",
        "duration",
        "speed",
        "speaker",
        "text",
        "style",
    ]

    with ui.Row():
        with ui.Column(scale=1):
            with ui.Group():
                ui.Markdown("📔Operator")

                add = ui.Button("➕ Add Line")
                add_break = ui.Button("➕ Add Break")
                undo = ui.Button("🔙 Remove Last")
                clear = ui.Button("🧹 Clear All")
                reload = ui.Button("🔄 Reload demo script")

        with ui.Column(scale=5):
            with ui.Group():
                ui.Markdown("📔Script")
                script_table = ui.DataFrame(
                    headers=table_headers,
                    datatype=["number", "str", "str", "str", "str", "str", "str"],
                    interactive=True,
                    wrap=True,
                    value=script_default_value,
                    row_count=(0, "dynamic"),
                    col_count=(len(table_headers), "fixed"),
                )

            send_to_ssml_btn = ui.Button("📩Send to SSML", variant="primary")

    def send_to_ssml(sheet: pd.DataFrame):
        if sheet.empty:
            raise ui.Error("Please add some text to the script table.")
        ssml = merge_dataframe_to_ssml(sheet)
        return (
            ui.Textbox(value=ssml),
            ui.Tabs(selected="ssml"),
            ui.Tabs(selected="ssml.editor"),
        )

    def _add_message(sheet: pd.DataFrame, data: pd.DataFrame):
        # 如果只有一行 并且是空的
        is_empty = sheet.empty or (sheet.shape[0] == 1 and "text" not in sheet.iloc[0]) or (sheet.shape[0] == 1 and sheet.iloc[0]["text"] == "")

        if is_empty:
            sheet = data
        else:
            sheet = pd.concat(
                [
                    sheet,
                    data,
                ],
                ignore_index=True,
            )
        return sheet

    def add_message(sheet: pd.DataFrame):
        data = pd.DataFrame(
            {
                "index": [sheet.shape[0]],
                "speaker": ["Bob"],
                "text": ["Hello"],
                "style": [""],
                "type": ["voice"],
                "duration": [""],
                "speed": [""],
            },
        )
        return _add_message(sheet, data)

    def add_break_line(sheet: pd.DataFrame):
        data = pd.DataFrame(
            {
                "index": [sheet.shape[0]],
                "speaker": [""],
                "text": [""],
                "style": [""],
                "type": ["break"],
                "duration": ["1s"],
                "speed": [""],
            },
        )
        return _add_message(sheet, data)

    def undo_message(sheet: pd.DataFrame):
        sheet = sheet.iloc[:-1]
        return sheet

    def clear_message():
        return pd.DataFrame(
            columns=table_headers,
        )

    def reload_message():
        return script_default_value

    add.click(fn=add_message, inputs=script_table, outputs=script_table)
    add_break.click(fn=add_break_line, inputs=script_table, outputs=script_table)
    undo.click(fn=undo_message, inputs=script_table, outputs=script_table)
    clear.click(fn=clear_message, inputs=None, outputs=script_table)
    reload.click(fn=reload_message, inputs=None, outputs=script_table)

    send_to_ssml_btn.click(
        send_to_ssml,
        inputs=[script_table],
        outputs=[
            ssml_input,
            tabs1,
            tabs2,
        ],
    )

    return script_table
