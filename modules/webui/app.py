"""The original studio's operations, arranged into panels for the React client."""

import os
from modules.studio import forms as ui
from modules.webui import webui_config
from modules.webui.localization_runtime import ENLocalizationVars, ZHLocalizationVars


def create_interface():
    from modules.webui.audio_tools.tools_tab import create_tools_tab
    from modules.webui.finetune.speaker_ft_tab import create_speaker_ft_tab
    from modules.webui.llm_podcast_tab import create_llm_podcast_tab
    from modules.webui.readme_tab import create_readme_tab
    from modules.webui.speaker_tab import create_speaker_panel
    from modules.webui.ssml.podcast_tab import create_ssml_podcast_tab
    from modules.webui.ssml.script_tab import create_script_tab
    from modules.webui.ssml.spliter_tab import create_spliter_tab
    from modules.webui.ssml.ssml_tab import create_ssml_interface
    from modules.webui.ssml.subtitle_tab import create_subtitle_tab
    from modules.webui.system_tab import create_system_tab
    from modules.webui.tts_tab import create_tts_interface
    from modules.core.models.zoo import model_zoo

    webui_config.localization = ENLocalizationVars() if os.getenv("DVA_LANGUAGE") == "en" else ZHLocalizationVars()
    webui_config.ssml_max = int(os.getenv("SSML_MAX_LEN", "5000"))
    webui_config.tts_max = int(os.getenv("TTS_MAX_LEN", "1000"))
    webui_config.max_batch_size = int(os.getenv("MAX_BATCH_SIZE", "8"))
    webui_config.experimental = os.getenv("WEBUI_EXPERIMENTAL", "").lower() in ("true", "1")
    with ui.Form() as form, ui.Blocks() as root, ui.Tabs() as tabs:
        with ui.Tab("TTS", id="tts"):
            create_tts_interface()
        with ui.Tab("SSML", id="ssml"), ui.Tabs() as sub:
            with ui.Tab("Editor", id="ssml.editor"):
                editor = create_ssml_interface()
            with ui.Tab("Script", id="ssml.script"):
                table = create_script_tab(editor, tabs, sub)
            with ui.Tab("长文本切分"):
                create_spliter_tab(editor, tabs, sub, table)
            with ui.Tab("多人播客"):
                create_ssml_podcast_tab(editor, tabs, sub, table)
            with ui.Tab("字幕导入"):
                create_subtitle_tab(editor, tabs, sub, table)
        with ui.Tab("音色管理"):
            create_speaker_panel()
        with ui.Tab("声音克隆"):
            source = ui.Audio(label="原始语音")
            reference = ui.Audio(label="目标音色参考语音")
            tau = ui.Slider(0.01, 1, value=0.3, step=0.01, label="转换强度 τ")
            output = ui.Audio(label="转换结果", format="wav")
            ui.Button("转换音色").click(lambda src, ref, t: model_zoo.get_model("open-voice").convert_audio(src, ref, t), [source, reference, tau], output)
        with ui.Tab("训练"):
            create_speaker_ft_tab(root)
        with ui.Tab("话题转 SSML 播客"):
            create_llm_podcast_tab()
        with ui.Tab("音频工具"), ui.Tabs():
            create_tools_tab()
        with ui.Tab("系统"):
            create_system_tab(root)
        with ui.Tab("使用说明"):
            create_readme_tab()
    return form
