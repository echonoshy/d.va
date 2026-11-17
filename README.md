# 🎮 D.VA - AI Podcast Creation Engine
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python Version](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/release/python-3120/)

> D.Va拥有一部强大的机甲，它具有两台全自动的近距离聚变机炮、可以使机甲飞跃敌人或障碍物的推进器、 还有可以抵御来自正面的远程攻击的防御矩阵
>
> —— From [OverWatch](http://ow.blizzard.cn/heroes/dva)

<p align="left">
  <img src="https://upload.wikimedia.org/wikipedia/zh/5/55/D.Va_Overwatch.png" width="200" height="200" alt="D.Va Overwatch" />
</p>

## 🚀 项目简介 (Introduction)

D.VA 是一个基于大模型优化的端到端多人TTS引擎，专注于播客节目创作。

https://github.com/user-attachments/assets/703eddfa-f641-4a23-b54f-c666a9263709

### ✨ 主要特性 (Features)

*   **端到端多人TTS**: 支持生成包含多个说话人的音频。
*   **定制化音色**: 允许用户设计和使用独特的音色。
*   **拟人化输出**: 生成更自然、更像人类说话的语音。
*   **背景音乐定制**: 支持添加和调整背景音乐。
*   **关键词生成播客**: 输入关键词即可自动生成多人音频播客节目。

### 🎧 音频示例 (Audio Demo)

[ai_podcast.webm](https://github.com/user-attachments/assets/a64f099a-7455-4142-af2f-0b68cb7e0679)

> 提示：如果无法在线播放，请尝试[下载音频文件](assets/ai_podcast_v1.MP3) (注意：此链接可能指向项目内的相对路径)。

## 🎯 应用场景 (Use Cases)

*   **AI语音新闻**: 自动生成每日AI语音新闻。
*   **内容创作**: 为播客频道、小红书等平台持续产出音频内容。

### 🗺️ 实现路径 (Workflow)

1.  🗞️ **智能采集**: 每日自动采集多领域专业新闻。
2.  ✂️ **稿件整理**: 自动分解整理成高质量新闻稿。
3.  🎤 **语音合成**: 转化为包含片头片尾的精美语音内容（建议时长控制在4分钟以内）。

## 🛠️ 快速上手 (Quick Start)

### 1️⃣ 环境准备 (Prerequisites)

*   **操作系统**: Linux (推荐)
*   **Python**: 3.12+
*   **系统依赖**: `ffmpeg`, `rubberband-cli`

```bash
# 更新包列表并安装系统依赖
sudo apt update
sudo apt install ffmpeg rubberband-cli git-lfs -y
```

### 2️⃣ 模型下载 (Download Models)

```bash
# 启用 Git LFS
git lfs install

# 在项目根目录运行，模型会下载到 models/ (选择一个源)
# Hugging Face (推荐)
git clone https://huggingface.co/echonoshy/d.va models

# 或者使用镜像站 (如果访问Hugging Face困难)
# git clone https://hf-mirror.com/echonoshy/d.va models
```

### 3️⃣ 安装依赖 (Install Dependencies)

推荐使用 `uv` 进行环境管理。

```bash
# 安装 uv (如果尚未安装)
# curl -LsSf https://astral.sh/uv/install.sh | sh
# source $HOME/.cargo/env
# 或者使用 pip 安装: pip install uv

# (可选) 更换为国内 PyPI 镜像源以加速下载
export UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

# (可选) 创建并激活虚拟环境 (如果需要指定Python版本)
# uv venv --python 3.12 .venv
# source .venv/bin/activate

# 使用 uv 同步依赖 (会自动读取 pyproject.toml)
uv sync

```
*注意：项目依赖定义在 `pyproject.toml` 中，推荐使用 `uv sync` 或 `pip install .` 来安装。*

### 4️⃣ 配置 (Configuration)

在项目根目录创建 `.env` 文件，并添加你的 DeepSeek API Key：

```dotenv
# .env
DEEPSEEK_API_KEY=your_api_key_here
```

### 5️⃣ 启动服务 (Launch)

启动 Web 界面：

```bash
uv run webui.py
```

或者直接使用 Python：

```bash
source .venv/bin/activate
python webui.py
```

## 📜 许可证 (License)

本项目采用 [GNU Affero General Public License v3.0](LICENSE)。

## 💖 致谢 (Acknowledgements)

本项目借鉴了众多开源项目的思路和解决方案，在此感谢他们的贡献：

*   [ChatTTS](https://github.com/2noise/ChatTTS)
*   [Awesome-ChatTTS](https://github.com/panyanyany/Awesome-ChatTTS)
*   [ChatTTS-Forge](https://github.com/lenML/ChatTTS-Forge)
*   [ChatTTS_WebUI](https://github.com/craii/ChatTTS_WebUI)
