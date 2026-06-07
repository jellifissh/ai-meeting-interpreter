import os
from dataclasses import dataclass

from openai import OpenAI


@dataclass
class TranscriptPolishResult:
    polished_transcript: str
    status: str
    used_fallback: bool


class TranscriptPolishService:
    """Polish raw ASR transcripts with DeepSeek and fallback to the raw text when needed."""

    _DEFAULT_BASE_URL = "https://api.deepseek.com"
    _DEFAULT_MODEL = "deepseek-chat"

    def polish(
        self,
        raw_transcript: str,
        source_language: str,
        meeting_scene: str,
    ) -> TranscriptPolishResult:
        normalized_raw_transcript = (raw_transcript or "").strip()
        if not normalized_raw_transcript:
            return TranscriptPolishResult(
                polished_transcript="",
                status="transcript polish fallback",
                used_fallback=True,
            )

        api_key = self._read_env("DEEPSEEK_API_KEY", "deepseek-api-key")
        if not api_key:
            return TranscriptPolishResult(
                polished_transcript=normalized_raw_transcript,
                status="transcript polish fallback",
                used_fallback=True,
            )

        base_url = self._read_env("DEEPSEEK_BASE_URL", "deep-seek-url") or self._DEFAULT_BASE_URL
        model = self._read_env("DEEPSEEK_MODEL") or self._DEFAULT_MODEL
        messages = self._build_messages(
            raw_transcript=normalized_raw_transcript,
            source_language=source_language,
            meeting_scene=meeting_scene,
        )

        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
            )
            polished_transcript = (response.choices[0].message.content or "").strip()
            if not polished_transcript:
                raise ValueError("Empty transcript polish response.")

            return TranscriptPolishResult(
                polished_transcript=polished_transcript,
                status="transcript polished success",
                used_fallback=False,
            )
        except Exception:
            return TranscriptPolishResult(
                polished_transcript=normalized_raw_transcript,
                status="transcript polish fallback",
                used_fallback=True,
            )

    def _build_messages(
        self,
        raw_transcript: str,
        source_language: str,
        meeting_scene: str,
    ) -> list[dict[str, str]]:
        system_prompt = (
            "You are a meeting ASR transcript polishing assistant. "
            "Fix obvious ASR errors, add punctuation, merge unnatural sentence breaks, "
            "and remove repeated words or meaningless filler words when they are clearly noise. "
            "Do not add new factual information. "
            "Do not summarize. "
            "Do not translate. "
            "Return only the polished original transcript."
        )
        user_prompt = "\n".join(
            [
                f"Source language: {source_language}",
                f"Meeting scene: {meeting_scene}",
                "Raw transcript:",
                raw_transcript,
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
