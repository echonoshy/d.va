import requests
from typing import Optional, Dict, Any

class SSMLService:
    def __init__(
        self, 
        base_url: str = "http://localhost:7870/v1/ssml",
        format: str = "mp3",
        batch_size: int = 16,
        speed_rate: float = 1.1
    ):
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        self.default_config = {
            "format": format,
            "batch_size": batch_size,
            "enhancer": {
                "enable": True,
                "model": "resemble-enhance"
            },
            "adjuster": {
                "speed_rate": speed_rate
            }
        }

    def generate_audio(
        self, 
        ssml_content: str,
        output_path: str,
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        payload = self.default_config.copy()
        if config:
            payload.update(config)
        payload["ssml"] = ssml_content

        try:
            response = requests.post(
                self.base_url, 
                json=payload, 
                headers=self.headers
            )
            
            if response.status_code == 200:
                with open(output_path, "wb") as audio_file:
                    audio_file.write(response.content)
                return True
            else:
                print(f"Request failed with status code: {response.status_code}")
                print(f"Response content: {response.text}")
                return False
                
        except Exception as e:
            print(f"Error generating audio: {str(e)}")
            return False