# AI Meeting Interpreter Demo

一个基于 Python + Gradio 的 AI 会议同传 Demo。当前版本支持麦克风录音或上传音频，优先使用本地 SenseVoiceSmall / FunASR 做离线语音识别，再调用 DeepSeek 做翻译；如果本地 ASR 或 DeepSeek 不可用，会自动 fallback，保证页面不崩。

## 当前能力

- 麦克风录音或上传 `mp3` / `wav` 音频
- 本地 ASR 识别原文
- DeepSeek 翻译译文
- 页面展示双语字幕结果
- 支持 near-real-time segmented interpreter demo
- 通过短音频切片 + 动态逐段输出模拟同传字幕体验
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
- 当前版本不是 WebSocket 工业级实时系统
- 通过短音频切片 + 动态逐段输出模拟同传字幕体验
- 首次运行本地 ASR 时，FunASR / SenseVoiceSmall 可能会下载模型文件
- 如果本地模型初始化失败，页面会继续使用 mock ASR 返回演示文本
- 如果未配置 `DEEPSEEK_API_KEY`，页面会继续使用 mock 翻译

## 后续方向

- 麦克风流式输入
- WebSocket
- VAD
- TTS
