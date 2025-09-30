import numpy as np
from pydub import AudioSegment
from modules.llm_ssml_service.ssml_service import DeepSeekClient
from modules.webui.webui_utils import synthesize_ssml


class PodcastPipeline:
    """Pipeline for generating podcast audio with background music"""

    def __init__(self, default_model: str = "deepseek-chat", default_bgm_path: str = "assets/bgm.mp3"):
        self.default_model = default_model
        self.default_bgm_path = default_bgm_path

    def pipeline(self, topic: str, model: str | None = None, bgm_path: str | None = None) -> None:
        """
        Run the complete podcast generation pipeline

        Args:
            topic: Topic for the podcast
            model: Optional, LLM model name
            bgm_path: Optional, background music path
        """
        ssml_content = self.generate_ssml(topic, model=model)
        if ssml_content:
            audio_data = synthesize_ssml(ssml=ssml_content, batch_size=16, enable_enhance=True, enable_denoise=True, speed_rate=1.1)
            if audio_data:
                self.audio_postprocess(audio_data, bgm_path=bgm_path or self.default_bgm_path)

    def clean_ssml_content(self, content: str) -> str:
        """Remove markdown code block markers from SSML content"""
        if content.startswith("```xml"):
            content = content.replace("```xml", "", 1)
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        return content.strip()

    def generate_ssml(self, topic: str, model: str | None = None) -> str | None:
        """Generate SSML content for the podcast"""
        client = DeepSeekClient()
        template_path = "modules/llm_ssml_service/template.txt"

        try:
            print(f"Generating SSML for topic: {topic}")
            content = client.generate_response(topic=topic, template_path=template_path, model=model or self.default_model)
            ssml_content = self.clean_ssml_content(content)
            print("SSML generation completed")
            return ssml_content

        except Exception as e:
            print(f"Error generating SSML: {str(e)}")
            return None

    def audio_postprocess(self, audio_data: tuple[int, np.ndarray], bgm_path: str = "assets/bgm.mp3", output_path: str = "final_output.mp3") -> bool:
        """
        Add background music to podcast audio

        Args:
            audio_data: Tuple of (sample_rate, audio_samples)
            bgm_path: Background music file path
            output_path: Output file path

        Returns:
            bool: True if processing successful, False otherwise
        """
        try:
            # Convert numpy array to AudioSegment
            sample_rate, samples = audio_data
            podcast = AudioSegment(samples.tobytes(), frame_rate=sample_rate, sample_width=samples.dtype.itemsize, channels=1)

            # Load and process background music
            bgm = AudioSegment.from_mp3(bgm_path)
            bgm_intro = bgm[:5000]  # First 5 seconds
            bgm_main = bgm[5000:]

            # Adjust background music length
            podcast_length = len(podcast)
            bgm_main_length = len(bgm_main)
            if bgm_main_length < podcast_length:
                repeats = (podcast_length // bgm_main_length) + 1
                bgm_main = bgm_main * repeats
            bgm_main = bgm_main[:podcast_length]

            # Adjust volume and add fade effects
            bgm_main = bgm_main - 25  # Reduce volume by 25dB
            bgm_main = bgm_main.fade_out(duration=3000)

            # Mix audio streams
            mixed = bgm_intro
            mixed = mixed.append(podcast.overlay(bgm_main), crossfade=500)

            # Export final audio
            mixed.export(output_path, format="mp3")
            print(f"Audio post-processing completed: {output_path}")
            return True

        except Exception as e:
            print(f"Audio post-processing failed: {str(e)}")
            return False


if __name__ == "__main__":
    podcast = PodcastPipeline()
    podcast.pipeline("What is work-life balance?")
