import os
from dataclasses import dataclass

from openai import OpenAI

from services.prompt_builder import PromptBuilder


@dataclass
class TranslationResult:
    translated_text: str
    status: str
    used_mock: bool


class TranslateService:
    """Translate text with DeepSeek and fallback to mock translations when needed."""

    _DEFAULT_BASE_URL = "https://api.deepseek.com"
    _DEFAULT_MODEL = "deepseek-chat"

    _MOCK_TRANSLATIONS = {
        (
            "中文→英文",
            "各位早上好，今天我们先同步项目进度，再讨论下周的交付安排。",
        ): "Good morning everyone. Let's review the project progress first, and then discuss next week's delivery plan.",
        (
            "中文→英文",
            "当前版本已经完成接口联调，但我们还需要解决高并发场景下的延迟问题。",
        ): "The current version has completed API integration, but we still need to address latency issues under high concurrency.",
        (
            "中文→英文",
            "本季度营收整体符合预期，但我们需要继续关注现金流和成本控制。",
        ): "Revenue this quarter is broadly in line with expectations, but we need to continue focusing on cash flow and cost control.",
        (
            "中文→英文",
            "你好，请先简单介绍一下你最近负责的项目，以及你在其中承担的核心职责。",
        ): "Hello. Please briefly introduce the recent project you were responsible for and the core role you played in it.",
        (
            "英文→中文",
            "Good morning everyone, let's review the project status first and then align on next week's delivery plan.",
        ): "各位早上好，今天我们先回顾项目进度，然后对齐下周的交付计划。",
        (
            "英文→中文",
            "The current release has completed API integration, but we still need to reduce latency under high concurrency.",
        ): "当前版本已经完成接口联调，但我们仍需要降低高并发场景下的延迟。",
        (
            "英文→中文",
            "Revenue for this quarter is in line with expectations, but we need to keep watching cash flow and cost control.",
        ): "本季度营收符合预期，但我们仍需持续关注现金流和成本控制。",
        (
            "英文→中文",
            "Hi, could you briefly introduce the latest project you worked on and explain your core responsibilities?",
        ): "你好，请简单介绍一下你最近参与的项目，并说明你的核心职责。",
    }

    def __init__(self, prompt_builder: PromptBuilder | None = None) -> None:
        self.prompt_builder = prompt_builder or PromptBuilder()

    def translate(
        self,
        source_text: str,
        direction: str,
        meeting_scene: str,
        context_text: str | None = None,
    ) -> TranslationResult:
        api_key = self._read_env("DEEPSEEK_API_KEY", "deepseek-api-key")

        if not api_key:
            return TranslationResult(
                translated_text=self._mock_translate(source_text, direction),
                status="DeepSeek API key not configured, fallback to mock translation.",
                used_mock=True,
            )

        base_url = self._read_env("DEEPSEEK_BASE_URL", "deep-seek-url") or self._DEFAULT_BASE_URL
        model = self._read_env("DEEPSEEK_MODEL") or self._DEFAULT_MODEL
        messages = self.prompt_builder.build_translation_messages(
            source_text=source_text,
            direction=direction,
            meeting_scene=meeting_scene,
            recent_context=context_text,
        )

        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
            )
            translated_text = (response.choices[0].message.content or "").strip()

            if not translated_text:
                raise ValueError("Empty translation response.")

            return TranslationResult(
                translated_text=translated_text,
                status="处理成功",
                used_mock=False,
            )
        except Exception:
            return TranslationResult(
                translated_text=self._mock_translate(source_text, direction),
                status="DeepSeek translation failed, fallback to mock translation.",
                used_mock=True,
            )

    def _mock_translate(self, source_text: str, direction: str) -> str:
        return self._MOCK_TRANSLATIONS.get((direction, source_text), "未找到匹配的 mock 译文。")

    @staticmethod
    def _read_env(*keys: str) -> str | None:
        for key in keys:
            value = os.getenv(key)
            if value:
                return value.strip()
        return None
