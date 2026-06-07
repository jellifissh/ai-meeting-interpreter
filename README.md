# AI Meeting Interpreter Demo

一个基于 Python + Gradio 的 AI 同声传译助手 Demo。当前版本聚焦稳定交付：用户可以录制完整会议音频或直接上传音频，系统会执行本地 ASR、转写文本智能清洗、DeepSeek 翻译，并输出双语字幕时间轴。

## Demo Video

- Demo video link: `[TODO: replace with demo video URL]`

## Screenshots

- Runtime screenshot: `[TODO: replace with screenshot image or link]`

## 当前版本说明

- 稳定模式适合完整音频和正式演示
- 支持麦克风录音 / 上传音频
- 支持分段字幕时间轴动态输出
- 使用本地 ASR + DeepSeek 翻译
- 支持对 ASR 转写文本进行智能清洗，用于修复断句、标点和明显识别错误
- 支持会议摘要、关键词和待办/结论提取
- 当前不是工业级 WebSocket 实时系统
- 后续可扩展云端 Streaming ASR、WebSocket、VAD、TTS

## 当前能力

- 麦克风录音或上传 `mp3` / `wav` 音频
- 本地 ASR 识别原文
- ASR 转写文本智能清洗
- DeepSeek 翻译译文
- AI 会议理解：摘要、关键词、待办/结论
- 页面展示双语字幕时间轴
- 稳定模式：完整音频 -> 本地 ASR -> Transcript Polish -> DeepSeek 翻译 -> 双语字幕时间轴
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
- 稳定模式适合完整音频和正式演示
- 当前版本不是工业级 WebSocket 实时系统
- 通过短音频切片 + 动态逐段输出模拟同传字幕体验
- 系统支持对 ASR 转写文本进行智能清洗，用于修复断句、标点和明显识别错误
- 系统支持会议摘要、关键词和待办/结论提取
- 首次运行本地 ASR 时，FunASR / SenseVoiceSmall 可能会下载模型文件
- 如果本地模型初始化失败，页面会继续使用 mock ASR 返回演示文本
- 如果未配置 `DEEPSEEK_API_KEY`，页面会继续使用 mock 翻译

## 后续方向

- 云端 Streaming ASR
- 麦克风 streaming
- WebSocket
- VAD
- TTS
