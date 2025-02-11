import gradio as gr
import logging
from pipeline import PodcastPipeline
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('podcast_generation.log')
    ]
)
logger = logging.getLogger(__name__)

def generate_podcast(topic: str) -> tuple[str, str]:
    """
    生成播客内容
    
    Args:
        topic: 播客主题
        
    Returns:
        tuple: (日志信息, 音频文件路径)
    """
    logger.info(f"开始处理主题: {topic}")
    
    try:
        # 创建输出目录
        os.makedirs("outputs", exist_ok=True)
        
        # 初始化pipeline
        pipeline = PodcastPipeline()
        
        # 生成内容
        logger.info("开始生成SSML...")
        pipeline.generate_ssml(topic)
        
        logger.info("开始生成音频...")
        pipeline.generate_audio()
        
        logger.info("开始音频后期处理...")
        output_path = "outputs/final_output.mp3"
        pipeline.audio_postprocess(
            podcast_path="output.mp3",
            bgm_path="assets/bgm.mp3",
            output_path=output_path
        )
        
        log_msg = f"处理完成！主题: {topic}"
        logger.info(log_msg)
        return log_msg, output_path
        
    except Exception as e:
        error_msg = f"处理失败: {str(e)}"
        logger.error(error_msg)
        return error_msg, None

# 创建Gradio界面
iface = gr.Interface(
    fn=generate_podcast,
    inputs=[
        gr.Textbox(
            label="播客主题",
            placeholder="请输入要讨论的话题...",
            lines=2
        )
    ],
    outputs=[
        gr.Textbox(label="处理状态", lines=1),
        gr.Audio(label="生成的播客")
    ],
    title="D.VA - AI播客生成器",
    description="输入话题，自动生成播客内容",
    examples=[
        ["聊聊程序员35岁危机"],
        ["人工智能会取代人类工作吗"],
        ["如何平衡工作和生活"]
    ],
    allow_flagging="never"
)

if __name__ == "__main__":
    iface.launch(
        server_name="0.0.0.0",
        server_port=7880,
        share=True
    )
