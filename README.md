# AI Meeting Interpreter Demo

一个基于 Python + Gradio 的 AI 同声传译助手 Demo。当前版本重点演示“麦克风录制式准实时同传”体验：用户可以录制或上传会议音频，系统会将音频切分为短片段，逐段执行本地 ASR 和 DeepSeek 翻译，并动态生成双语字幕时间轴。

## Demo Video

- Demo video link: `[TODO: replace with demo video URL]`

## Screenshots

- Runtime screenshot: `[TODO: replace with screenshot image or link]`

## 当前版本说明

- 当前版本是麦克风录制式准实时同传 Demo
- 支持麦克风录音 / 上传音频
- 支持分段字幕时间轴动态输出
- 使用本地 ASR + DeepSeek 翻译
- 不是工业级 WebSocket 实时系统
- 后续可扩展云端 Streaming ASR、WebSocket、VAD、TTS

## 当前能力

- 麦克风录音或上传 `mp3` / `wav` 音频
- 本地 ASR 识别原文
- DeepSeek 翻译译文
- 页面展示双语字幕时间轴
- 动态逐段输出 near-real-time segmented interpreter demo
- ASR 初始化失败时自动 fallback 到 mock ASR
- 翻译失败或未配置 API Key 时自动 fallback 到 mock translation

## 运行方式

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 配置环境变量

```bash
copy .env.example .env
```

3. 启动应用

```bash
python app.py
```

## 说明

- 当前版本支持麦克风录音和上传音频
- 当前版本是 near-real-time segmented interpreter demo
- 当前版本不是工业级 WebSocket 实时系统
- 通过短音频切片 + 动态逐段输出模拟同传字幕体验
- 首次运行本地 ASR 时，FunASR / SenseVoiceSmall 可能会下载模型文件
- 如果本地模型初始化失败，页面会继续使用 mock ASR 返回演示文本
- 如果未配置 `DEEPSEEK_API_KEY`，页面会继续使用 mock 翻译

## 后续方向

- 云端 Streaming ASR
- WebSocket
- VAD
- TTS
