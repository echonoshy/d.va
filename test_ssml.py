import requests

# ssml_content = "<speak version='0.1'><voice>Hello, world!</voice></speak>"

ssml_content = """
<speak version="0.1">

    <voice spk="有磁性的男播音" style="narration-relaxed">
        各位代码打工人、摸鱼艺术家、咖啡因依赖症患者们 [uv_break]，欢迎收听《码上暴富》！今天咱们聊点刺激的——个人开发者如何用键盘撬动地球，实现从"码畜"到"老板"的阶级跃迁！[laugh]
    </voice>

    <voice spk="声音有点像陈一发" style="narration-relaxed">
        老王你清醒点 [uv_break]，我昨天刚因为写bug被产品经理追杀到凌晨三点，现在听到"创业"两个字只想用键盘砸自己的头... [uv_break]
    </voice>

    <voice spk="有磁性的男播音" style="narration-relaxed">
        年轻人，这就是你还在打工的原因！[laugh] 你想想，同样是熬夜 [uv_break]，给自己写代码和给老板写代码，心态能一样吗？来，先说说你最大的顾虑是啥？
    </voice>

    <voice spk="声音有点像陈一发" style="narration-relaxed">
        启动资金不够、不会推广、怕被抄袭、没时间... [uv_break] 最要命的是！我上次独立开发的"AI鉴渣神器"APP，用户注册数还没我奶奶的广场舞队友多！[uv_break]
    </voice>

    <voice spk="有磁性的男播音" style="narration-relaxed">
        哈哈哈哈！[laugh] 好家伙，你知道问题出在哪吗？[uv_break] 你给广场舞阿姨们演示产品的时候，是不是穿着格子衫顶着黑眼圈，开口就是"这个算法基于Transformer架构..."？[laugh]
    </voice>

    <voice spk="声音有点像陈一发" style="narration-relaxed">
        你怎么知道？！[uv_break]
    </voice>

    <voice spk="有磁性的男播音" style="narration-relaxed">
        划重点！创业第一课——把你的技术焦虑转化成用户爽点！[uv_break] 你说"分布式缓存"，用户听到的是"卡成PPT"；你说"机器学习模型"，用户想到的是"人工智障"。[laugh] 要学学煎饼果子摊主，人家不说面粉蛋白质含量，只说"加两个蛋管饱"！[laugh]
    </voice>

    <voice spk="声音有点像陈一发" style="narration-relaxed">
        所以我要把"基于LSTM的情感分析"翻译成"一秒看透渣男小作文"？[uv_break]
    </voice>

</speak>

"""





url = "http://localhost:7870/v1/ssml"  # 请将此 URL 替换为实际的 API 端点

headers = {
    "Content-Type": "application/json"
}

payload = {
    "ssml": ssml_content,
    "format": "mp3",
    "batch_size": 16,
    "enhancer": {
        "enable": True,
        "model": "resemble-enhance",
    },
    "adjuster": {
        "speed_rate": 1.3
    }
}

response = requests.post(url, json=payload, headers=headers)

if response.status_code == 200:
    print("请求成功!")
    print("音频内容类型：", response.headers.get("content-type"))
    # 将返回的音频内容保存为 MP3 文件
    with open("output2.mp3", "wb") as audio_file:
        audio_file.write(response.content)
        print("音频已保存为 output2.mp3")
else:
    print(f"请求失败，状态码: {response.status_code}")
    print("响应内容：", response.text)