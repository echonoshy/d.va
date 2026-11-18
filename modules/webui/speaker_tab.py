from modules.studio import forms as ui

from modules.webui.speaker.speaker_creator import speaker_creator_ui
from modules.webui.speaker.speaker_editor import speaker_editor_ui
from modules.webui.speaker.speaker_editor_v2 import speaker_editor_ui_v2
from modules.webui.speaker.speaker_merger import create_speaker_merger
import os


def create_speaker_panel():
    with ui.Tabs():
        with ui.Tab("Builder"):
            speaker_editor_ui_v2()
        with ui.Tab("Test Voice"):
            speaker_editor_ui()
        with ui.Tab("ChatTTS"), ui.Tabs():
            with ui.Tab("Creator"):
                speaker_creator_ui()
            with ui.Tab("Merger"):
                create_speaker_merger()
        with ui.Tab("Hub"):
            ui.Hub(value=os.getenv("SPKS_INDEX", ""))
