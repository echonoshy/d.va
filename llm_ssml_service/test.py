from openai import OpenAI
import os 
from dotenv import load_dotenv

load_dotenv()


url = 'https://api.siliconflow.cn/v1/'
# api_key = 'sk-xxxx'
api_key = os.getenv('SILICONFLOW_API_KEY')

model = 'deepseek-ai/DeepSeek-R1'
# model = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"     # 测试


client = OpenAI(
    base_url=url,
    api_key=api_key,
    timeout=600.0  # 设置 10 分钟超时
)

def read_prompt_template(template_path: str) -> str:
    """读取prompt模板文件"""
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read().strip()

def format_prompt(template: str, topic: str) -> str:
    """格式化prompt模板"""
    return template.format(topic=topic)

if __name__ == "__main__":
    # 读取模板
    template_path = "llm_ssml_service/template.txt"
    prompt_template = read_prompt_template(template_path)
    
    # 设置主题
    topic = "程序员如何低成本创业？"
    
    # 格式化提示词
    prompt = format_prompt(prompt_template, topic)
    
    try:
        # 发送非流式输出的请求
        messages = [
            {"role": "user", "content": prompt}
        ]
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=False, 
            max_tokens=4096,
            timeout=600  # 设置 10 分钟超时
        )
        content = response.choices[0].message.content

        print(f"Topic: {topic}")
        print(f"Prompt: {prompt}")
        print("-" * 50)
        print(content)
        print("*" * 100)
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        raise