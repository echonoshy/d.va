# D.Va 语音与播客工作室

D.Va 在本机完成语音合成、多角色 SSML 配音、音色卡制作、ChatTTS 音色训练和 OpenVoice 声音转换。网页使用 TypeScript 和 React，模型推理和训练继续使用 Python。导航栏同时保留了双人播客编辑台。

## 启动完整工作室

需要 Node.js 22.12 或更新版本、Python 3.12、uv、FFmpeg 和 Rubber Band。macOS 可以用 `brew install uv ffmpeg rubberband` 安装系统工具。Linux 上的对应软件包通常叫 `ffmpeg` 和 `rubberband-cli`。

在项目根目录运行以下命令。

```sh
npm ci
uv sync --frozen
python3 scripts/install-studio-models.py
npm run build
npm start
```

打开 [本地工作室](http://127.0.0.1:8787/)。首次进入模型页面会启动 Python 工作进程。模型按需载入内存。下载脚本按固定版本和摘要核验模型，已有匹配文件会复用。也可以在命令后写一个或多个组名 `ChatTTS`、`fish-speech-1_4`、`OpenVoiceV2`、`resemble-enhance`。勾选增强或降噪需要最后一组。原有模型放在项目的 `models/` 下，保留各自子目录名。

## 选择工作入口

| 想做的事 | 在界面中的操作 |
| --- | --- |
| 文本配音 | 进入「TTS」，选择 ChatTTS 或 FishSpeech。可选已有音色、上传卡片或录入参考音频。ChatTTS 支持种子、口语化和停顿标记，FishSpeech 可用一段清晰的语音及其逐字稿作参考。结果可以试听、下载和回听前两次生成。 |
| 多人配音 | 进入「SSML」，直接编辑 XML，或用脚本表格编排说话人、台词、风格和停顿。长文本切分、多人播客和字幕都能送回编辑器或表格。支持 SRT、ASS、VTT。 |
| 制作或安装音色卡 | 在「音色管理」填写资料、试听样本和参考音频，导出 `.spkv1.json`，也可以保存到本地音色库。ChatTTS 子页支持种子生成、试音和最多四个音色的加权融合。音色目录支持加载索引、搜索、筛选、排序及安装。 |
| 转换已有录音的音色 | 在「声音克隆」提供原始语音和目标音色参考语音，调节转换强度后导出 WAV。 |
| 训练 ChatTTS 音色 | 在「训练」刷新数据集，可设置初始音色、学习率、轮数、批量大小和文本损失。页面显示训练日志并支持停止。生成的卡片写入 `data/speakers/`。 |
| 生成播客 | 「播客编辑台」可以手写或生成脚本、逐段修改、为两位角色配音、加配乐并导出 MP3。「话题转 SSML 播客」保留了原来的话题 → SSML → 多人配音 → 配乐流程，并返回生成的 SSML。 |
| 调整音频或提取视频音轨 | 「音频工具」支持调整速度、音高、增益、响度、增强和降噪，也可以从视频提取音轨。 |
| 管理模型 | 「系统」显示内存和推理设备，可卸载模型或重新载入已加载的模型。 |

### 训练数据

例如将清单放在 `datasets/data_demo/voices.list`，录音放在 `datasets/data_demo/demo/001.wav`。清单使用 UTF-8 编码，每行的音频路径相对于清单目录。

```text
demo/001.wav|demo|zh|你好，欢迎收听今天的节目。
```

在训练页点「刷新数据集」后选择该清单。训练结束后，在 TTS 页刷新音色下拉框，或直接上传导出的 JSON 卡片。已有清单也可使用命令行。

```sh
uv run python -m modules.finetune.train_speaker --data_path datasets/data_demo/voices.list --epochs 10 --batch_size 4 --lr 0.01 --save_folder data/speakers
```

### 可选服务与旧接口

- 将 `.env.example` 复制为 `.env`，设置 `DEEPSEEK_API_KEY` 和账号可用的 `DEEPSEEK_MODEL` 即可用话题生成。调用时主题会发送给 DeepSeek。本机语音合成、SSML 编辑、音色制作和训练可以离线运行。
- 双人编辑台支持 macOS 系统语音、Linux 的 eSpeak、可选的中文 AISHELL-3 音色，以及兼容 `/v1/audio/speech` 的服务。`npm run model:install` 安装 AISHELL-3，已有目录可用 `DVA_MODEL_DIR` 指定。自定义服务使用 `DVA_TTS_BASE_URL`、`DVA_TTS_MODEL`、`DVA_TTS_VOICES` 和可选的 `DVA_TTS_API_KEY`。
- `uv run python webui.py --api` 在本机 7860 端口同时提供 React 页面和原有模型 API。`--server_port` 可改端口。也可以用 `DVA_ENABLE_API=1 npm start` 将接口挂到 8787。启动后可访问同端口的 `/docs`。单独运行 API 使用 `uv run python -m modules.studio.legacy_api`。
- `WEBUI_EXPERIMENTAL=1` 显示旧版的提示词参数。`TTS_MAX_LEN`、`SSML_MAX_LEN` 和 `MAX_BATCH_SIZE` 控制表单上限。`SPKS_INDEX` 可指定自己的音色目录索引。该目录和卡片地址须允许浏览器跨域读取，也可直接导入本地卡片。
- 英文数字规范化可离线运行。Linux x86-64 上可用 `uv sync --frozen --extra english-tn` 安装旧管线的完整 WeText 英文规则。
- 旧启动器的 Gradio 公网分享隧道已随界面替换。服务默认仅绑定本机。macOS 默认使用 CPU 全精度，CUDA 机器自动选择 GPU。

## 验证

```sh
npm run build
npm test
uv run python -m unittest discover -s tests
```

[查看与 5518052 的功能核对表](docs/5518052-parity.md)。源码许可证见 [LICENSE](LICENSE)。模型权重和附带的第三方源码保留各自的使用条款。
