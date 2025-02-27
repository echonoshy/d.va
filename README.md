# 🎮 D.VA - AI Podcast Creation Engine

> D.Va拥有一部强大的机甲，它具有两台全自动的近距离聚变机炮、可以使机甲飞跃敌人或障碍物的推进器、 还有可以抵御来自正面的远程攻击的防御矩阵

—— From [OverWatch](http://ow.blizzard.cn/heroes/dva)

<img src="https://upload.wikimedia.org/wikipedia/zh/5/55/D.Va_Overwatch.png" width="200" height="200" />

## 🚀 项目简介

D.VA 是一个基于大模型优化的端到端多人TTS引擎，专注于播客节目创作。项目的目标是让AI辅助创作变得简单而有趣。

https://github.com/user-attachments/assets/703eddfa-f641-4a23-b54f-c666a9263709

### 音频示例
[ai_podcast.webm](https://github.com/user-attachments/assets/a64f099a-7455-4142-af2f-0b68cb7e0679)
> 提示：如果无法在线播放，请[点击下载](assets/ai_podcast_v1.MP3)

## 🛠️ 快速上手

### 1️⃣ 模型安装
```bash
cd models/
git lfs install
git clone https://huggingface.co/echonoshy/d.va
```

### 2️⃣ 依赖安装
```bash
# 系统依赖
apt install ffmpeg rubberband-cli

# Python依赖
pip install -r requirements.txt
```

### 3️⃣ 配置与启动
在项目根目录创建`.env`文件，并添加：
```
SILICONFLOW_API_KEY=your_api_key_here
```

启动Web界面：
```bash
python webui.py
```

## 🎯 应用场景

想象一下：每天自动更新的AI语音新闻，为您的播客频道和小红书账号源源不断地产出优质内容，轻松涨粉！

### 🗺️ 实现路径
1. 🗞️ 每日智能采集多领域专业新闻
2. ✂️ 自动分解整理成高质量新闻稿
3. 🎤 转化为精美语音内容（含片头片尾，时长控制在4分钟以内）
4. 📱 一键推送至小红书和各大播客平台

## 🌟 即将到来的新特性

- [ ] 🎭 声音克隆功能 - 用您喜欢的声音讲述故事
- [ ] 🎨 自定义音色系统 - 打造专属于您的声音标识
- [x] ⚡ 优化TTS API访问速度 - 让创作更加流畅
- [ ] 🔮 更多场景支持 - 敬请期待...

## 💖 致谢

本项目借鉴了众多开源项目的思路和解决方案，在此感谢他们的贡献：

- [ChatTTS](https://github.com/2noise/ChatTTS)
- [Awesome-ChatTTS](https://github.com/panyanyany/Awesome-ChatTTS)
- [ChatTTS-Forge](https://github.com/lenML/ChatTTS-Forge)
- [ChatTTS_WebUI](https://github.com/craii/ChatTTS_WebUI)
