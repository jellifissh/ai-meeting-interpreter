# AI Meeting Interpreter

## 演示视频

百度网盘链接：https://pan.baidu.com/s/1AJDToxHi5mfRkTNaiW9O-A?pwd=1111  
提取码：1111

## 项目简介

这是一个面向会议场景的 AI 同声传译与会议理解系统，支持麦克风录音或上传会议音频。  
系统会自动完成本地语音识别、转写文本清洗、场景化翻译、双语字幕时间轴生成，并提取会议摘要、关键词和待办/结论。  
最终页面使用 Gradio + 自定义 CSS 进行产品化展示。

## 核心功能

- 麦克风录音 / 上传会议音频
- 本地 ASR 语音识别
- ASR 转写文本智能清洗
- DeepSeek 场景化翻译
- 双语字幕时间轴
- AI 会议理解：摘要、关键词、待办/结论
- 异常 fallback，保证页面稳定运行

## 技术栈

- Python
- Gradio
- FunASR / SenseVoiceSmall
- DeepSeek / OpenAI-compatible API
- ffmpeg

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

## 项目亮点

- 采用 ASR -> Transcript Polish -> LLM Translation -> Subtitle Timeline 的完整处理链路
- 支持不同会议场景下的翻译策略调整
- 通过 Transcript Polish 提升 ASR 转写文本可读性
- 输出双语字幕和会议理解结果，适合会议复盘和内容整理

## 开发过程

项目按功能模块分阶段开发与提交，主要包括页面骨架、本地 ASR 语音识别、DeepSeek 翻译、Transcript Polish 文本清洗、双语字幕时间轴、AI 会议理解和页面展示优化等阶段。

## 第三方依赖说明

本项目使用 Gradio 构建交互页面，使用 FunASR / SenseVoiceSmall 完成本地语音识别，使用 OpenAI-compatible SDK 调用 DeepSeek 进行翻译和会议理解，并使用 ffmpeg、librosa、soundfile 等工具完成音频预处理。

项目原创实现部分包括：音频处理流程编排、ASR 结果清洗、场景化翻译 Prompt、双语字幕时间轴生成、AI 会议理解输出、Gradio 页面交互与整体工程集成。
