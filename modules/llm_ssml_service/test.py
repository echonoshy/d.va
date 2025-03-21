from ssml_service import DeepSeekClient

def main():
    client = DeepSeekClient()
    template_path = "template.txt"
    topic = "程序员如何低成本创业？"
    
    try:
        content = client.generate_response(
            topic=topic,
            template_path=template_path
        )
        
        print(f"Topic: {topic}")
        print("-" * 50)
        print(content)
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()