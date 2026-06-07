import os
from dataclasses import dataclass

from openai import OpenAI


@dataclass
class InsightResult:
    insight_text: str
    status: str
    available: bool


class InsightService:
    """Extract meeting summary, keywords, and action items from polished transcripts."""

    _DEFAULT_BASE_URL = "https://api.deepseek.com"
    _DEFAULT_MODEL = "deepseek-chat"
    _FALLBACK_TEXT = "AI 会议理解暂不可用。"

    def extract(self, polished_transcript: str, meeting_scene: str) -> InsightResult:
        normalized_transcript = (polished_transcript or "").strip()
        if not normalized_transcript:
            return InsightResult(
                insight_text=self._FALLBACK_TEXT,
                status="AI meeting insights unavailable",
                available=False,
            )

        api_key = self._read_env("DEEPSEEK_API_KEY", "deepseek-api-key")
        if not api_key:
            return InsightResult(
                insight_text=self._FALLBACK_TEXT,
                status="AI meeting insights unavailable",
                available=False,
            )

        base_url = self._read_env("DEEPSEEK_BASE_URL", "deep-seek-url") or self._DEFAULT_BASE_URL
        model = self._read_env("DEEPSEEK_MODEL") or self._DEFAULT_MODEL

        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=model,
                messages=self._build_messages(normalized_transcript, meeting_scene),
                temperature=0.2,
            )
            insight_text = (response.choices[0].message.content or "").strip()
            if not insight_text:
                raise ValueError("Empty insight response.")

            return InsightResult(
                insight_text=insight_text,
                status="AI meeting insights ready",
                available=True,
            )
        except Exception:
            return InsightResult(
                insight_text=self._FALLBACK_TEXT,
                status="AI meeting insights unavailable",
                available=False,
            )

    def _build_messages(self, polished_transcript: str, meeting_scene: str) -> list[dict[str, str]]:
        system_prompt = (
            "You are an AI meeting understanding assistant. "
            "Based on the provided meeting transcript, extract meeting insights using exactly this format:\n"
            "摘要：\n"
            "...\n\n"
            "关键词：\n"
            "...\n\n"
            "待办/结论：\n"
            "...\n\n"
            "Do not translate the transcript. "
            "Do not use Markdown. "
            "Do not add any sections outside the required format."
        )
        user_prompt = "\n".join(
            [
                f"Meeting scene: {meeting_scene}",
                "Transcript:",
                polished_transcript,
            ]
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    @staticmethod
    def _read_env(*keys: str) -> str | None:
        for key in keys:
            value = os.getenv(key)
            if value:
                return value.strip()
        return None
