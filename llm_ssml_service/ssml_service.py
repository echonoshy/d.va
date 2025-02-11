from typing import Optional, Dict, Any
from openai import OpenAI
import os
from dotenv import load_dotenv

class SiliconFlowClient:    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        base_url: str = 'https://api.siliconflow.cn/v1/',
        # model: str = 'deepseek-ai/DeepSeek-R1-Distill-Llama-70B',
        model: str = 'deepseek-ai/DeepSeek-R1-Distill-Llama-8B',
        timeout: float = 600.0
    ):
        if api_key is None:
            load_dotenv()
            api_key = os.getenv('SILICONFLOW_API_KEY')
            if not api_key:
                raise ValueError("API key not found in environment variables")
        
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout
        )
    
    @staticmethod
    def read_prompt_template(template_path: str) -> str:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    
    @staticmethod
    def format_prompt(template: str, topic: str) -> str:
        return template.format(topic=topic)
    
    def generate_response(
        self, 
        topic: str,
        template_path: str,
        stream: bool = False,
        max_tokens: int = 4096,
        **kwargs: Dict[str, Any]
    ) -> str:
        try:
            prompt_template = self.read_prompt_template(template_path)
            prompt = self.format_prompt(prompt_template, topic)
            
            messages = [{"role": "user", "content": prompt}]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=stream,
                max_tokens=max_tokens,
                timeout=self.timeout,
                **kwargs
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")