import gradio as gr
from pipeline import PodcastPipeline

def create_llm_podcast_tab():
    MODEL_OPTIONS = [
        "deepseek-ai/DeepSeek-R1",
        "Pro/deepseek-ai/DeepSeek-R1",
        "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
        "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
        "Pro/deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
        "Pro/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        "Pro/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
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
                
                bgm_input = gr.File(
                    label="背景音乐",
                    file_types=["audio"],
                    info="可选：上传自定义背景音乐（MP3格式）"
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
                
            pipeline = PodcastPipeline()
            
            try:
                # 处理BGM路径
                bgm_path = bgm.name if bgm else None
                
                # 运行pipeline
                pipeline.pipeline(
                    topic=topic,
                    model=model,
                    bgm_path=bgm_path
                )
                
                return pipeline.ssml_content, "final_output.mp3"
                
            except Exception as e:
                return f"生成失败: {str(e)}", None
                
        generate_btn.click(
            fn=generate_podcast,
            inputs=[topic_input, model_select, bgm_input],
            outputs=[ssml_output, audio_output]
        )
        
        return generate_btn
