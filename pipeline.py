import os
import requests 
from pydub import AudioSegment
from modules.llm_ssml_service.ssml_service import SiliconFlowClient


class PodcastPipeline:
    
    def __init__(
        self,
        default_model: str = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        default_bgm_path: str = "assets/bgm.mp3"
    ):
        self.default_model = default_model
        self.default_bgm_path = default_bgm_path
    
    def pipeline(
        self, 
        topic: str,
        model: str | None = None,
        bgm_path: str | None = None
    ):
        """
        运行完整的播客生成流程
        
        Args:
            topic: 播客主题
            model: 可选，LLM模型名称
            bgm_path: 可选，背景音乐路径
        """
        self.generate_ssml(topic, model=model)
        self.generate_audio()
        self.audio_postprocess(bgm_path=bgm_path or self.default_bgm_path)
        
    def clean_ssml_content(self, content: str) -> str:
        if content.startswith("```xml"):
            content = content.replace("```xml", "", 1)
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        return content.strip()
    
    def generate_ssml(self, topic: str, model: str | None = None):
        client = SiliconFlowClient()
        template_path = "modules/llm_ssml_service/template.txt"
        
        try:
            print(f"Start to generate ssml for this topic: {topic}")
            content = client.generate_response(
                topic=topic,
                template_path=template_path,
                model=model or self.default_model
            )
            self.ssml_content = self.clean_ssml_content(content)
            print("Generate done.")
            print(self.ssml_content)
        except Exception as e:
            print(f"Error: {str(e)}")
            
        
    def generate_audio(self):
        url = "http://localhost:7870/v1/ssml" 
        headers = {
            "Content-Type": "application/json"
        }
        
        # TODO: 通过配置文件修改
        payload = {
            "ssml": self.ssml_content,
            "format": "mp3",
            "batch_size": 16,
            "enhancer": {
                "enable": True,
                "model": "resemble-enhance",
            },
            "adjuster": {
                "speed_rate": 1.1
            }
        }
        
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            print("Audio generate done:")
            with open("output.mp3", "wb") as audio_file:
                audio_file.write(response.content)
                print("Audio saved to output.mp3")
                                
                
    def audio_postprocess(self, 
                         podcast_path: str = "output.mp3", 
                         bgm_path: str = "assets/bgm.mp3", 
                         output_path: str = "final_output.mp3") -> bool:
        """
        给播客音频添加背景音乐
        
        Args:
            podcast_path: 播客音频文件路径
            bgm_path: 背景音乐文件路径
            output_path: 输出文件路径
        """
        try:
            # 加载音频文件
            podcast = AudioSegment.from_mp3(podcast_path)
            bgm = AudioSegment.from_mp3(bgm_path)
            
            # 提取BGM前3秒
            bgm_intro = bgm[:5000]  # pydub中的时间单位是毫秒
            
            # 准备BGM主体部分（3秒后的部分）
            bgm_main = bgm[5000:]
            
            # 计算需要的BGM长度
            podcast_length = len(podcast)
            bgm_main_length = len(bgm_main)
            
            # 如果BGM较短，循环播放直到满足需要的长度
            if bgm_main_length < podcast_length:
                repeats = (podcast_length // bgm_main_length) + 1
                bgm_main = bgm_main * repeats
            
            # 截取需要的BGM长度
            bgm_main = bgm_main[:podcast_length]
            
            # 降低BGM音量到30%
            bgm_main = bgm_main - 20  # -10.5dB ≈ 30% 音量
            
            # 对BGM主体的最后3秒进行淡出处理
            fade_duration = 3000  # 3秒，单位毫秒
            bgm_main = bgm_main.fade_out(duration=fade_duration)
            
            # 合成最终音频：BGM前奏（3秒） + （播客+低音量BGM叠加）
            mixed = bgm_intro
            mixed = mixed.append(podcast.overlay(bgm_main), crossfade=500)
            
            # 导出文件
            mixed.export(output_path, format="mp3")
            print(f"后期处理完成，文件已保存至: {output_path}")
            return True
            
        except Exception as e:
            print(f"音频后期处理失败: {str(e)}")
            return False
    
    
    
    
if __name__ == "__main__":
    # 使用默认参数
    podcast = PodcastPipeline()
    podcast.pipeline("聊一聊躺平？")
    
    # 或者指定参数
    podcast.pipeline(
        "聊一聊躺平？",
        model="deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
        bgm_path="assets/custom_bgm.mp3"
    )
