class PromptBuilder:
    """Build prompt context for future ASR and current translation requests."""

    _SCENE_HINTS = {
        "通用会议": "Keep the translation formal, clear, and easy to follow in a business meeting.",
        "技术会议": "Keep technical terms accurate and preserve terms such as API, model, pipeline, latency, and deployment when appropriate.",
        "金融会议": "Keep financial terms accurate and preserve terms such as revenue, net profit, EPS, ROE, and valuation when appropriate.",
        "面试场景": "Keep the wording natural, conversational, and suitable for an interview discussion.",
    }

    _DIRECTION_HINTS = {
        "中文→英文": "Translate the Chinese input into natural, concise English suitable for meeting subtitles.",
        "英文→中文": "Translate the English input into natural, accurate Chinese suitable for meeting subtitles.",
    }

    def build(self, direction: str, scene: str, audio_filename: str) -> dict:
        return {
            "direction": direction,
            "scene": scene,
            "audio_filename": audio_filename,
            "scene_hint": self._SCENE_HINTS.get(scene, ""),
        }

    def build_translation_messages(
        self,
        source_text: str,
        direction: str,
        meeting_scene: str,
    ) -> list[dict[str, str]]:
        direction_hint = self._DIRECTION_HINTS.get(direction, "Translate the input for meeting subtitles.")
        scene_hint = self._SCENE_HINTS.get(meeting_scene, "Keep the translation clear and suitable for a live meeting.")

        system_prompt = (
            "You are a professional real-time meeting interpreter. "
            f"{direction_hint} "
            f"{scene_hint} "
            "Return only the translation text. "
            "Do not explain. Do not use Markdown. "
            "Do not add prefixes such as 'Translation' or '以下是翻译'."
        )

        user_prompt = (
            f"Translation direction: {direction}\n"
            f"Meeting scene: {meeting_scene}\n"
            "Source text:\n"
            f"{source_text}"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
