# D.Va 播客工作室

在浏览器里编写双人对话，给主持人和嘉宾选音色，再把整期节目导出为 MP3。可以从手写脚本开始，也可以用 DeepSeek 根据话题起草，再逐段修改。上传配乐后，工作室会把它循环铺在对白下方。

## 启动

需要 Node.js 22.12 或更高版本，以及带 libmp3lame 编码器的 FFmpeg。macOS 可以直接使用系统自带的语音；Linux 可安装 eSpeak NG。在 Ubuntu 或 Debian 上运行 `sudo apt install ffmpeg espeak-ng`，在 macOS 上可用 `brew install ffmpeg`。

```sh
npm ci
npm run build
npm start
```

打开 **http://127.0.0.1:8787**。首次尝试可以直接使用编辑台中的示例。给两个角色选好音色后点击「生成 MP3」，在「成品试听」播放或下载。脚本和下载结果仅保存在当前页面中，刷新前请下载要保留的节目。

### 本地中文神经音色

```sh
npm run model:install
```

该命令从 sherpa-onnx 官方发布下载约 30 MiB 的 AISHELL-3 模型包，核对 SHA-256 并将运行所需的文件安装到 `models/vits-icefall-zh-aishell3/`。刷新编辑台即可选择中文神经音色。模型使用 CPU 合成，适合普通话对白。编辑台从 174 位说话人中提供 8 个音色供选择；其他语言可以使用系统语音或配置语音服务。安装这一模型也需要系统的 `tar` 支持 bzip2 解压。

如果已经下载了官方压缩包，可以运行 `npm run model:install -- /path/to/vits-icefall-zh-aishell3.tar.bz2`。已有解压目录可以通过 `DVA_MODEL_DIR` 指定。模型及训练数据遵循各自的使用条款，项目源码与模型分开发行。[模型说明与示例](https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/vits.html#aishell3-chinese-multi-speaker-174-speakers) · [模型发布](https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models)

### 用话题起草脚本

在项目根目录复制 `.env.example` 为 `.env`，填写 `DEEPSEEK_API_KEY`，重启服务。点击「话题生成」后输入主题，生成的对话可以继续编辑。通过 `DEEPSEEK_MODEL` 选择账号可用的模型。手写脚本和本机配音均可离线使用。

### 使用已有的语音服务

在 `.env` 中填写 `DVA_TTS_BASE_URL`（例如 `http://127.0.0.1:8000/v1`）、`DVA_TTS_MODEL` 和逗号分隔的 `DVA_TTS_VOICES`。如果服务需要认证，再填写 `DVA_TTS_API_KEY`。重启后，编辑台会使用这些服务端音色。语音端点需要支持 `POST /audio/speech` 并返回音频。

选择话题生成时，服务会向 DeepSeek 发送主题；选择兼容语音服务时，台词会发往所配置的端点。本机系统语音与本地 ONNX 推理直接在运行 D.Va 的电脑上处理台词。密钥仅由服务器读取。服务器默认监听回环地址；要开放给其他人，应在入口配置鉴权和 HTTPS。

## 项目与验收

- `web/src/` 是 React 编辑台。运行 `npm run build` 后，由同一 Node 服务提供页面和 API。
- `server/` 实现脚本生成、声线选择、音频合成与混音。配乐上限 20 MiB，每次请求单独使用临时目录，返回 MP3 后清理文件。默认端口可通过 `PORT` 设置，FFmpeg 可通过 `FFMPEG_PATH` 指定。
- `npm test` 运行 HTTP 和音频回归。要运行真实系统语音与混音用例，请安装 FFmpeg 及可用的系统语音引擎。安装中文模型后还可直接验证双音色神经合成。
- `npm audit --audit-level=low` 检查 npm 锁文件。源码采用 [AGPL-3.0](LICENSE)。

这个版本移除了旧 Gradio 页面、Python 训练和声音克隆工具、自带的第三方模型源码及其依赖。此前保存的模型文件可继续在原版本中使用；新版使用上述声线来源。
