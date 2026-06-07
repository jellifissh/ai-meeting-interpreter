class PromptBuilder:
    """Build prompt context for future ASR and current translation requests."""

    _SCENE_CONFIG = {
        "通用会议": {
            "strategy": "正式、自然、清晰，适合会议字幕，去掉无意义口头语。",
            "prompt_hint": "Keep the translation formal, natural, and clear for meeting subtitles. Remove meaningless filler words when appropriate.",
            "terms": "General business language; no special terminology constraints beyond clarity.",
        },
        "技术会议": {
            "strategy": "保留或准确翻译技术术语，风格简洁、准确。",
            "prompt_hint": "Preserve or accurately translate technical terminology. Keep the wording concise and precise.",
            "terms": "API, pipeline, latency, deployment, model, WebSocket, chunk, fallback, frontend, backend",
        },
        "金融会议": {
            "strategy": "保留金融术语和指标，风格专业、简洁。",
            "prompt_hint": "Preserve financial terminology and metrics. Keep the tone professional and concise.",
            "terms": "revenue, net profit, EPS, ROE, PE, PB, valuation, growth rate, YoY, QoQ",
        },
        "面试场景": {
            "strategy": "自然、口语化，适合面试交流，保留项目经历、技术栈、团队协作表达，避免过度书面化。",
            "prompt_hint": "Keep the wording natural and conversational for an interview. Preserve project experience, tech stack, and teamwork expressions without sounding overly formal.",
            "terms": "project experience, tech stack, ownership, collaboration, delivery, problem solving",
        },
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
            "scene_hint": self._scene_prompt_hint(scene),
        }

    def describe_scene_strategy(self, scene: str) -> str:
        scene_config = self._SCENE_CONFIG.get(scene, {})
        strategy = scene_config.get("strategy", "正式、自然、清晰，适合会议字幕。")
        terms = scene_config.get("terms", "No special terminology hints.")
        return f"场景：{scene}\n策略：{strategy}\n术语提示：{terms}"

    def build_translation_messages(
        self,
        source_text: str,
        direction: str,
        meeting_scene: str,
        recent_context: str | None = None,
    ) -> list[dict[str, str]]:
        direction_hint = self._DIRECTION_HINTS.get(direction, "Translate the input for meeting subtitles.")
        scene_hint = self._scene_prompt_hint(meeting_scene)
        scene_strategy = self._scene_strategy(meeting_scene)
        scene_terms = self._scene_terms(meeting_scene)

        system_prompt = (
            "You are a professional real-time meeting interpreter. "
            f"{direction_hint} "
            f"{scene_hint} "
            "Use recent context only to improve continuity and subtitle naturalness. "
            "If the current chunk is a partial sentence, translate it naturally based on context, "
            "but only translate the current chunk itself. "
            "Return only the translation text. "
            "Do not explain. Do not use Markdown. "
            "Do not add prefixes such as 'Translation' or '以下是翻译'."
        )

        user_prompt_lines = [
            f"Translation direction: {direction}",
            f"Meeting scene: {meeting_scene}",
            f"Scene translation strategy: {scene_strategy}",
            f"Scene terminology hints: {scene_terms}",
        ]
        if recent_context:
            user_prompt_lines.extend(
                [
                    "Recent context for continuity only:",
                    recent_context,
                ]
            )
        user_prompt_lines.extend(
            [
                "Current chunk to translate:",
                source_text,
            ]
        )
        user_prompt = "\n".join(user_prompt_lines)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _scene_prompt_hint(self, scene: str) -> str:
        return self._SCENE_CONFIG.get(scene, {}).get(
            "prompt_hint",
            "Keep the translation clear and suitable for a live meeting.",
        )

    def _scene_strategy(self, scene: str) -> str:
        return self._SCENE_CONFIG.get(scene, {}).get(
            "strategy",
            "正式、自然、清晰，适合会议字幕。",
        )

    def _scene_terms(self, scene: str) -> str:
        return self._SCENE_CONFIG.get(scene, {}).get(
            "terms",
            "No special terminology hints.",
        )
