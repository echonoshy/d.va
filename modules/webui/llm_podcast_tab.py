import os
from pathlib import Path
from tempfile import TemporaryDirectory

from modules.studio import forms as ui
from pipeline import PodcastPipeline

# Initialize pipeline once
podcast_pipeline = PodcastPipeline()


def create_llm_podcast_tab():
    MODEL_OPTIONS = list(dict.fromkeys([os.getenv("DEEPSEEK_MODEL", "deepseek-flash"), "deepseek-flash", "deepseek-v4-pro"]))

    with ui.Tab("LLM Podcast"):
        with ui.Row():
            with ui.Column():
                topic_input = ui.Textbox(label="Topic", placeholder="请输入要讨论的话题，如：聊一聊躺平", lines=1)

                model_select = ui.Dropdown(
                    choices=MODEL_OPTIONS,
                    value=MODEL_OPTIONS[0],  # 默认选择70B模型
                    label="选择模型",
                    info="选择用于生成内容的模型",
                )

                bgm_input = ui.Audio(
                    label="背景音乐",
                    type="filepath",
                )

                generate_btn = ui.Button("生成播客", variant="primary")

            with ui.Column():
                ssml_output = ui.Textbox(label="生成的SSML内容", lines=15, interactive=False)

        with ui.Row():
            audio_output = ui.Audio(label="生成的音频", type="filepath")

        def generate_podcast(topic, model, bgm):
            if not topic:
                return "请输入话题", None

            try:
                # Generate SSML content
                ssml_content = podcast_pipeline.generate_ssml(topic, model=model)
                if not ssml_content:
                    return "SSML 生成失败，请重试", None

                # Generate and process audio
                audio_data = podcast_pipeline.synthesize_speech(ssml_content)
                if not audio_data:
                    return "音频生成失败，请重试", None

                # Post-process audio with BGM
                with TemporaryDirectory() as directory:
                    output_path = str(Path(directory) / "podcast.mp3")
                    success = podcast_pipeline.audio_postprocess(audio_data, bgm_path=bgm or podcast_pipeline.default_bgm_path, output_path=output_path)
                    if not success:
                        return "音频后期处理失败，请重试", None
                    return ssml_content, audio_output.move_resource_to_block_cache(output_path)

            except Exception as e:
                error_msg = f"生成过程发生错误: {str(e)}"
                print(error_msg)
                return error_msg, None

        generate_btn.click(fn=generate_podcast, inputs=[topic_input, model_select, bgm_input], outputs=[ssml_output, audio_output])

        return generate_btn
