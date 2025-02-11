from modules.llm_ssml_service.ssml_service import SiliconFlowClient




class PodcastPipeline:
    
    def __init__(self):
        pass
    
    def pipeline(self, topic):
        self.generate_ssml(topic)
        self.generate_audio()
        
        
    def generate_ssml(self, topic):
        client = SiliconFlowClient()
        template_path = "modules/llm_ssml_service/template.txt"
        
        try:
            print(f"Start to generate ssml for this topic: {topic}")
            self.ssml_content = client.generate_response(
                topic=topic,
                template_path=template_path
            )
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
                
                
                
    def audio_postprocess(self):
        # 增加背景音乐等
        pass 
    
    
    
    
    
if __name__ == "__main__":
    podcast = PodcastPipeline()
    podcast.pipeline("聊一聊躺平？")
    