class MockASRService:
    """Mock ASR layer for the MVP. Replace this with a real provider later."""

    _MOCK_TRANSCRIPTS = {
        ("中文→英文", "通用会议"): "各位早上好，今天我们先同步项目进度，再讨论下周的交付安排。",
        ("中文→英文", "技术会议"): "当前版本已经完成接口联调，但我们还需要解决高并发场景下的延迟问题。",
        ("中文→英文", "金融会议"): "本季度营收整体符合预期，但我们需要继续关注现金流和成本控制。",
        ("中文→英文", "面试场景"): "你好，请先简单介绍一下你最近负责的项目，以及你在其中承担的核心职责。",
        ("英文→中文", "通用会议"): "Good morning everyone, let's review the project status first and then align on next week's delivery plan.",
        ("英文→中文", "技术会议"): "The current release has completed API integration, but we still need to reduce latency under high concurrency.",
        ("英文→中文", "金融会议"): "Revenue for this quarter is in line with expectations, but we need to keep watching cash flow and cost control.",
        ("英文→中文", "面试场景"): "Hi, could you briefly introduce the latest project you worked on and explain your core responsibilities?",
    }

    def transcribe(self, audio_path: str, context: dict) -> str:
        key = (context["direction"], context["scene"])
        return self._MOCK_TRANSCRIPTS.get(key, "未找到匹配的 mock 原文。")
