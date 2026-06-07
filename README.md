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
