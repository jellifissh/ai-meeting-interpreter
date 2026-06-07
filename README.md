# AI Meeting Interpreter Demo

一个基于 Python + Gradio 的 AI 会议同传助手 Demo。当前版本使用 mock ASR 生成演示原文，翻译服务接入 DeepSeek / OpenAI-compatible API；如果没有配置 API Key，系统会自动 fallback 到 mock 翻译，保证 Demo 可运行。

## 功能

- 上传音频文件
- 选择翻译方向
  - 中文→英文
  - 英文→中文
- 选择会议场景
  - 通用会议
  - 技术会议
  - 金融会议
  - 面试场景
- 点击按钮后返回结果
  - 原文：由 mock ASR 根据方向和场景返回模拟会议发言
  - 译文：优先使用 DeepSeek 真实翻译；未配置或调用失败时自动使用 mock 翻译
  - 状态：展示真实翻译成功或 fallback 说明

## 项目结构

```text
.
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── services
    ├── asr_service.py
    ├── translate_service.py
    └── prompt_builder.py
```

## 环境变量

标准配置：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

当前版本也兼容读取你现有 Windows 环境变量：

- `deepseek-api-key`
- `deep-seek-url`

说明：

- `DEEPSEEK_BASE_URL` 未配置时，默认使用 `https://api.deepseek.com`
- `DEEPSEEK_MODEL` 未配置时，默认使用 `deepseek-chat`
- `DEEPSEEK_API_KEY` 未配置时，自动 fallback 到 mock 翻译

## 运行方式

1. 创建虚拟环境

```bash
python -m venv .venv
```

2. 激活虚拟环境

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

3. 安装依赖

```bash
pip install -r requirements.txt
```

4. 配置环境变量

```bash
copy .env.example .env
```

然后按需填写 DeepSeek 配置。

5. 启动应用

```bash
python app.py
```

启动后，Gradio 会在本地输出访问地址，打开浏览器即可使用。

## 实现说明

- `app.py`：Gradio 页面和交互入口
- `services/asr_service.py`：mock ASR 服务，当前不接入真实语音识别模型
- `services/translate_service.py`：DeepSeek / OpenAI-compatible 翻译服务，内置 mock fallback
- `services/prompt_builder.py`：根据翻译方向和会议场景构造提示词

## 翻译策略

- 中文→英文：输出自然、简洁、适合会议字幕的英文
- 英文→中文：输出自然、准确、适合会议字幕的中文
- 通用会议：保持正式、清晰
- 技术会议：保留技术术语，如 API、模型、pipeline、latency、deployment
- 金融会议：保留金融术语，如 revenue、net profit、EPS、ROE、valuation
- 面试场景：表达自然，适合面试交流

模型被明确约束为：

- 只返回译文
- 不返回解释
- 不输出 Markdown
- 不添加“以下是翻译”等前缀

## 当前限制

- 当前版本仍使用 mock ASR，不接入真实语音识别
- 不包含数据库
- 不包含登录注册
- 不使用 WebSocket
- 不做复杂前后端分离

## 后续计划

- 接入 FunASR / SenseVoiceSmall 做本地免费语音识别
- 增加更细的术语表控制，提高技术和金融场景的一致性
- 增加基础日志和异常观测，方便排查 API 调用问题
- 在保留当前分层结构的前提下接入流式翻译体验
