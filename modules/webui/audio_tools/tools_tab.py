from modules.studio import forms as ui

from modules.webui.audio_tools.post_process import create_post_processor
from modules.webui.audio_tools.video_cut import create_audio_separator


def create_tools_tab():
    with ui.TabItem("Post Process"):
        create_post_processor()
    with ui.TabItem("Video Cut"):
        create_audio_separator()
