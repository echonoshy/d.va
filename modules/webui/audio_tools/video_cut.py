from modules.studio import forms as ui
import tempfile
import soundfile as sf


def create_audio_separator():
    """
    创建音频分离组件
    """

    def extract_audio(video_path: str):
        if not video_path:
            raise ValueError("请选择有音轨的视频")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as output:
            name = output.name
        with sf.SoundFile(video_path) as audio, sf.SoundFile(name, "w", audio.samplerate, audio.channels, format="mp3") as encoded:
            for block in audio.blocks(blocksize=65536):
                encoded.write(block)
        return name

    with ui.Row():
        with ui.Column(scale=3):
            input_video = ui.Video(label="Input Video", sources=["upload"])
        with ui.Column(scale=6):
            output_audio = ui.Audio(label="提取的音频")
            btn = ui.Button("提取音频", variant="primary")

        # 设置按钮点击后的回调函数
        btn.click(
            fn=extract_audio,
            inputs=[input_video],
            outputs=[output_audio],
        )
