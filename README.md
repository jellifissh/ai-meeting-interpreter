# AI Meeting Interpreter Demo

一个基于 Python + Gradio 的 AI 同声传译助手 Demo。当前版本包含两个入口：稳定模式用于完整音频的分段字幕演示，实验模式用于 5-10 秒短句的麦克风实时字幕演示。

## Demo Video

- Demo video link: `[TODO: replace with demo video URL]`

## Screenshots

- Runtime screenshot: `[TODO: replace with screenshot image or link]`

## 当前版本说明

- 稳定模式适合完整音频和正式演示
- 实验麦克风模式适合短句实时字幕演示
- 支持麦克风录音 / 上传音频
- 支持分段字幕时间轴动态输出
- 使用本地 ASR + DeepSeek 翻译
- 当前不是工业级 WebSocket 实时系统
- 后续可扩展云端 Streaming ASR、WebSocket、VAD、TTS

## 当前能力

- 麦克风录音或上传 `mp3` / `wav` 音频
- 本地 ASR 识别原文
- DeepSeek 翻译译文
- 页面展示双语字幕时间轴
- 稳定模式：完整音频 -> 分段字幕时间轴
- 实验模式：5-10 秒短句 -> 麦克风实时字幕追加
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
- 实验麦克风模式适合 5-10 秒短句实时字幕演示
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
