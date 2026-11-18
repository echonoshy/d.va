from modules.studio import forms as ui

from modules.webui.finetune.speaker_ft_tab import create_speaker_ft_tab


def create_ft_tabs(demo):
    with ui.Tabs():
        with ui.TabItem("Speaker"):
            create_speaker_ft_tab(demo)
        with ui.TabItem("GPT"):
            ui.Markdown("🚧 Under construction")
        with ui.TabItem("AE"):
            ui.Markdown("🚧 Under construction")
