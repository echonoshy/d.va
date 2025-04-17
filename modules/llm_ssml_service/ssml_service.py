import os
from dotenv import load_dotenv
from openai import OpenAI


class DeepSeekClient:    
    def __init__(
        self, 
        api_key: str | None = None,
        base_url: str = 'https://api.deepseek.com/',
        timeout: float = 600.0,
        default_model: str = 'deepseek-chat'
    ):
        if api_key is None:
            load_dotenv()
            api_key = os.getenv('DEEPSEEK_API_KEY')
            if not api_key:
                raise ValueError("DeepSeek API key not found in environment variables")
        
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model
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
        model: str | None = None,
        stream: bool = False,
        max_tokens: int = 8192,
        system_message: str = "You are a helpful assistant.",
        **kwargs: dict[str, str]
    ) -> str:
        try:
            prompt_template = self.read_prompt_template(template_path)
            prompt = self.format_prompt(prompt_template, topic)
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                stream=stream,
                max_tokens=max_tokens,
                timeout=self.timeout,
                **kwargs
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"Error generating response with DeepSeek API: {str(e)}")
