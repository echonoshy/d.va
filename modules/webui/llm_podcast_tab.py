import gradio as gr
from pipeline import PodcastPipeline

def create_llm_podcast_tab():
    with gr.Tab("LLM Podcast"):
        with gr.Row():
            with gr.Column():
                topic_input = gr.Textbox(
                    label="Topic",
                    placeholder="请输入要讨论的话题，如：聊一聊躺平",
                    lines=1
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
            
        def generate_podcast(topic):
            if not topic:
                return "请输入话题", None
                
            pipeline = PodcastPipeline()
            
            try:
                # 生成SSML
                pipeline.generate_ssml(topic)
                ssml_content = pipeline.ssml_content
                
                # 生成音频
                pipeline.generate_audio()
                
                # 后期处理
                pipeline.audio_postprocess()
                
                return ssml_content, "final_output.mp3"
                
            except Exception as e:
                return f"生成失败: {str(e)}", None
                
        generate_btn.click(
            fn=generate_podcast,
            inputs=[topic_input],
            outputs=[ssml_output, audio_output]
        )
        
        return generate_btn
