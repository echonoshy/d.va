import gradio as gr
from pipeline import PodcastPipeline
from modules.webui.webui_utils import synthesize_ssml

# Initialize pipeline once
podcast_pipeline = PodcastPipeline()

def create_llm_podcast_tab():
    MODEL_OPTIONS = [
        "deepseek-chat",
        "deepseek-reasoner"
    ]

    with gr.Tab("LLM Podcast"):
        with gr.Row():
            with gr.Column():
                topic_input = gr.Textbox(
                    label="Topic",
                    placeholder="请输入要讨论的话题，如：聊一聊躺平",
                    lines=1
                )
                
                model_select = gr.Dropdown(
                    choices=MODEL_OPTIONS,
                    value=MODEL_OPTIONS[2],  # 默认选择70B模型
                    label="选择模型",
                    info="选择用于生成内容的模型"
                )
                
                bgm_input = gr.Audio(
                    label="背景音乐(mp3)",
                )
                
                generate_btn = gr.Button("生成播客", variant="primary")
                
            with gr.Column():
                ssml_output = gr.Textbox(
                    label="生成的SSML内容",
                    lines=15,
                    interactive=False
                )
                
        with gr.Row():
            audio_output = gr.Audio(
                label="生成的音频",
                type="filepath"
            )
            
        def generate_podcast(topic, model, bgm):
            if not topic:
                return "请输入话题", None

            try:
                # Process BGM path
                bgm_path = bgm.name if bgm else None
                
                # Generate SSML content
                ssml_content = podcast_pipeline.generate_ssml(topic, model=model)
                if not ssml_content:
                    return "SSML 生成失败，请重试", None

                # Generate and process audio
                audio_data = synthesize_ssml(
                    ssml=ssml_content,
                    batch_size=16,
                    enable_enhance=True,
                    enable_denoise=True,
                    speed_rate=1.1
                )
                if not audio_data:
                    return "音频生成失败，请重试", None

                # Post-process audio with BGM
                success = podcast_pipeline.audio_postprocess(
                    audio_data,
                    bgm_path=bgm_path or podcast_pipeline.default_bgm_path
                )
                if not success:
                    return "音频后期处理失败，请重试", None

                return ssml_content, "final_output.mp3"

            except Exception as e:
                error_msg = f"生成过程发生错误: {str(e)}"
                print(error_msg)
                return error_msg, None

        generate_btn.click(
            fn=generate_podcast,
            inputs=[topic_input, model_select, bgm_input],
            outputs=[ssml_output, audio_output]
        )

        return generate_btn
