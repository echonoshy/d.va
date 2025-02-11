from ssml_service import SSMLService

def main():
    # 创建服务实例
    ssml_service = SSMLService()
    
    # 假设ssml_content从其他函数获得
    ssml_content = get_ssml_content()  # 你需要实现这个函数
    
    # 生成音频
    success = ssml_service.generate_audio(
        ssml_content=ssml_content,
        output_path="output.mp3"
    )
    
    if success:
        print("Audio saved successfully")
    else:
        print("Failed to generate audio")

if __name__ == "__main__":
    main()