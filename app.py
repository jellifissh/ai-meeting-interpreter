from pathlib import Path
import re

import gradio as gr
from dotenv import load_dotenv

from services.asr_service import LocalASRService
from services.insight_service import InsightService
from services.prompt_builder import PromptBuilder
from services.transcript_polish_service import TranscriptPolishService
from services.translate_service import TranslateService


load_dotenv()


APP_TITLE = "AI Meeting Interpreter Demo"
TRANSLATION_DIRECTIONS = ["中文→英文", "英文→中文"]
MEETING_SCENES = ["通用会议", "技术会议", "金融会议", "面试场景"]
PROCESSING_MODES = ["分段字幕（推荐）", "整段翻译"]
DEFAULT_SEGMENT_DURATION_SECONDS = 8
ENGLISH_SENTENCE_WORD_THRESHOLD = 12
CHINESE_SENTENCE_CHAR_THRESHOLD = 18
APP_THEME = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="blue",
    neutral_hue="slate",
).set(
    body_background_fill="*neutral_50",
    block_background_fill="white",
    block_border_width="0px",
    block_label_background_fill="transparent",
    block_label_text_color="*neutral_800",
    block_label_text_weight="600",
    block_title_background_fill="transparent",
    block_shadow="0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)",
)

APP_CSS = """
:root {
    --text-main: #0f172a;
    --text-sub: #64748b;
    --chip-bg: #eef2ff;
    --chip-text: #4338ca;
}

body, .gradio-container {
    background-color: #f8fafc !important;
    background-image: radial-gradient(#e2e8f0 1px, transparent 1px) !important;
    background-size: 20px 20px !important;
}

.gradio-container {
    max-width: 1400px !important;
    margin: 0 auto;
    padding: 30px 20px !important;
}

/* 顶部 Header 重新排版，更加紧凑现代 */
.header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 24px;
    margin-bottom: 24px;
    background: white;
    border-radius: 16px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.header-copy h1 {
    margin: 0;
    color: var(--text-main);
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.5px;
}

.header-copy p {
    margin: 4px 0 0;
    color: var(--text-sub);
    font-size: 13px;
}

.header-chips {
    display: flex;
    gap: 8px;
}

.chip {
    padding: 6px 12px;
    border-radius: 8px;
    background: var(--chip-bg);
    color: var(--chip-text);
    font-size: 12px;
    font-weight: 600;
}

/* 杀掉所有残留的内部边框 */
.gr-block, .gr-group, .block {
    border: none !important;
}

/* 统一输入框和文本域的质感 */
textarea, .wrap, input {
    border-radius: 12px !important;
    border: 1px solid #e2e8f0 !important;
    background: #f8fafc !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
    padding: 12px !important;
}

/* 按钮更加醒目 */
.primary-action button {
    background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important;
    border: none !important;
    color: white !important;
    min-height: 48px !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 16px !important;
    box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.3) !important;
    transition: transform 0.1s ease !important;
}

.primary-action button:active {
    transform: scale(0.98) !important;
}

/* 控制高度，防止撑破 */
.output-box textarea { height: 400px !important; }
.strategy-box textarea { height: 120px !important; background: #fffbeb !important; border-color: #fde68a !important; color: #92400e !important;}
"""

prompt_builder = PromptBuilder()
asr_service = LocalASRService()
insight_service = InsightService()
transcript_polish_service = TranscriptPolishService()
translate_service = TranslateService(prompt_builder=prompt_builder)


def run_demo(
    audio_file: str | None,
    direction: str,
    scene: str,
    processing_mode: str,
):
    if not audio_file:
        yield "", "", _format_status_display("请先录制或上传音频"), [], ""
        return

    audio_path = Path(audio_file)
    context = prompt_builder.build(direction=direction, scene=scene, audio_filename=audio_path.name)

    if processing_mode == "分段字幕（推荐）":
        yield from _run_segmented_demo(audio_path, context, direction, scene)
        return

    yield _run_full_audio_demo(audio_path, context, direction, scene)


def _clean_full_transcript(parts: list[str]) -> str:
    merged = " ".join(part.strip() for part in parts if part and part.strip())
    merged = re.sub(r"\s+", " ", merged).strip()
    merged = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", merged)
    merged = re.sub(r"([。！？!?])\s+", r"\1", merged)
    merged = re.sub(r"\s+([,.;:，。！？；：])", r"\1", merged)
    return merged


def _clean_chunk_text(text: str) -> str:
    cleaned = text.replace("\r", " ").replace("\n", " ")
    cleaned = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", cleaned)
    cleaned = re.sub(r"\s+([,.;:，。！？；：])", r"\1", cleaned)
    return cleaned


def _merge_buffer_text(existing_text: str, new_text: str) -> str:
    return _clean_full_transcript([existing_text, new_text])


def _build_recent_context(source_parts: list[str], limit: int = 2) -> str | None:
    recent_parts = [part for part in source_parts[-limit:] if part]
    if not recent_parts:
        return None
    return _clean_full_transcript(recent_parts)


def _count_cjk_chars(text: str) -> int:
    return sum(1 for char in text if "\u4e00" <= char <= "\u9fff")


def _count_english_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text))


def _is_sentence_ready(text: str) -> bool:
    normalized_text = _clean_chunk_text(text)
    if not normalized_text:
        return False

    if normalized_text.endswith((".", "?", "!", "。", "？", "！")):
        return True

    if _count_english_words(normalized_text) >= ENGLISH_SENTENCE_WORD_THRESHOLD:
        return True

    if _count_cjk_chars(normalized_text) >= CHINESE_SENTENCE_CHAR_THRESHOLD:
        return True

    return False


def _source_language_from_direction(direction: str) -> str:
    return "中文" if direction == "中文→英文" else "英文"


def _scene_strategy_text(scene: str) -> str:
    return prompt_builder.describe_scene_strategy(scene)


def _build_meeting_insight(polished_transcript: str, scene: str) -> str:
    return insight_service.extract(polished_transcript=polished_transcript, meeting_scene=scene).insight_text


def _format_status_display(status: str) -> str:
    normalized = (status or "").strip()
    if not normalized:
        return ""
    lowered = normalized.lower()
    if normalized == "请先录制或上传音频":
        return f"🎙️ {normalized}"
    if normalized.startswith("处理完成"):
        return f"✅ {normalized}"
    if normalized.startswith("正在") or normalized.startswith("已输出"):
        return f"⏳ {normalized}"
    if "fallback" in lowered or "failed" in lowered or "失败" in normalized:
        return f"⚠️ {normalized}"
    return f"ℹ️ {normalized}"


def _run_full_audio_demo(
    audio_path: Path,
    context: dict,
    direction: str,
    scene: str,
) -> tuple[str, str, str, list[list[str]], str]:
    asr_result = asr_service.transcribe(audio_path=str(audio_path), context=context)
    polish_result = transcript_polish_service.polish(
        raw_transcript=asr_result.transcript,
        source_language=_source_language_from_direction(direction),
        meeting_scene=scene,
    )
    polished_transcript = _clean_full_transcript([polish_result.polished_transcript or asr_result.transcript])
    translation_result = translate_service.translate(
        source_text=polished_transcript,
        direction=direction,
        meeting_scene=scene,
    )

    status_parts = [asr_result.status, polish_result.status, translation_result.status]
    status = _format_status_display(" | ".join(part for part in status_parts if part))
    timeline_rows = [["整段", asr_result.transcript, translation_result.translated_text, status]]
    insight_text = _build_meeting_insight(polished_transcript, scene)

    return polished_transcript, translation_result.translated_text, status, timeline_rows, insight_text


def _run_segmented_demo(
    audio_path: Path,
    context: dict,
    direction: str,
    scene: str,
):
    try:
        segments = asr_service.segment_audio(
            str(audio_path),
            segment_duration_seconds=DEFAULT_SEGMENT_DURATION_SECONDS,
        )
    except Exception as exc:
        full_source, full_translation, full_status, timeline_rows, insight_text = _run_full_audio_demo(
            audio_path,
            context,
            direction,
            scene,
        )
        fallback_status = _format_status_display(
            f"Segmented subtitle mode failed: {exc}. Fallback to full-audio mode. | {full_status}"
        )
        yield full_source, full_translation, fallback_status, timeline_rows, insight_text
        return

    timeline_rows: list[list[str]] = []
    source_parts: list[str] = []
    translated_parts: list[str] = []
    asr_success_count = 0
    translation_success_count = 0
    fallback_segment_count = 0
    pending_text = ""
    pending_start_time = ""
    pending_end_time = ""
    pending_status_parts: list[str] = []

    total_segments = len(segments)
    yield "", "", _format_status_display(f"正在处理：第 0 / {total_segments} 段，ASR 成功 0 段，翻译成功 0 段。"), [], ""

    for index, segment in enumerate(segments, start=1):
        segment_context = dict(context)
        asr_result = asr_service.transcribe(audio_path=segment.audio_path, context=segment_context)
        cleaned_source_text = _clean_chunk_text(asr_result.transcript)

        if cleaned_source_text:
            pending_text = _merge_buffer_text(pending_text, cleaned_source_text)
            if not pending_start_time:
                pending_start_time = segment.start_time
            pending_end_time = segment.end_time
        pending_status_parts.extend([segment.status, asr_result.status])

        if not asr_result.used_mock and "success" in asr_result.status.lower():
            asr_success_count += 1
        if asr_result.used_mock:
            fallback_segment_count += 1

        cumulative_source = _clean_full_transcript(source_parts)
        cumulative_translation = _clean_full_transcript(translated_parts)
        progress_status = (
            f"正在缓存语义片段，第 {index} / {total_segments} 段，"
            f"ASR 成功 {asr_success_count} 段，"
            f"翻译成功 {translation_success_count} 段。"
        )

        if pending_text and _is_sentence_ready(pending_text):
            recent_context = _build_recent_context(source_parts)
            translation_result = translate_service.translate(
                source_text=pending_text,
                direction=direction,
                meeting_scene=scene,
                context_text=recent_context,
            )
            cleaned_translated_text = _clean_chunk_text(translation_result.translated_text)
            pending_status_parts.append(translation_result.status)
            combined_status = " | ".join(part for part in pending_status_parts if part)

            source_parts.append(pending_text)
            translated_parts.append(cleaned_translated_text)

            if not translation_result.used_mock and translation_result.status == "处理成功":
                translation_success_count += 1
            else:
                fallback_segment_count += 1

            timeline_rows.append(
                [
                    f"{pending_start_time} - {pending_end_time}",
                    pending_text,
                    cleaned_translated_text,
                    combined_status,
                ]
            )

            cumulative_source = _clean_full_transcript(source_parts)
            cumulative_translation = _clean_full_transcript(translated_parts)
            progress_status = (
                f"已输出语义片段，第 {index} / {total_segments} 段，"
                f"ASR 成功 {asr_success_count} 段，"
                f"翻译成功 {translation_success_count} 段。"
            )
            pending_text = ""
            pending_start_time = ""
            pending_end_time = ""
            pending_status_parts = []

        yield cumulative_source, cumulative_translation, _format_status_display(progress_status), list(timeline_rows), ""

    if pending_text:
        recent_context = _build_recent_context(source_parts)
        translation_result = translate_service.translate(
            source_text=pending_text,
            direction=direction,
            meeting_scene=scene,
            context_text=recent_context,
        )
        cleaned_translated_text = _clean_chunk_text(translation_result.translated_text)
        pending_status_parts.append(translation_result.status)
        combined_status = " | ".join(part for part in pending_status_parts if part)

        source_parts.append(pending_text)
        translated_parts.append(cleaned_translated_text)

        if not translation_result.used_mock and translation_result.status == "处理成功":
            translation_success_count += 1
        else:
            fallback_segment_count += 1

        timeline_rows.append(
            [
                f"{pending_start_time} - {pending_end_time}",
                pending_text,
                cleaned_translated_text,
                combined_status,
            ]
        )

    raw_full_source = _clean_full_transcript(source_parts)
    polish_result = transcript_polish_service.polish(
        raw_transcript=raw_full_source,
        source_language=_source_language_from_direction(direction),
        meeting_scene=scene,
    )
    polished_full_source = _clean_full_transcript([polish_result.polished_transcript or raw_full_source])
    final_translation_result = translate_service.translate(
        source_text=polished_full_source,
        direction=direction,
        meeting_scene=scene,
    )
    full_translation = _clean_full_transcript([final_translation_result.translated_text])

    final_status = (
        f"处理完成：共 {total_segments} 段，"
        f"ASR 成功 {asr_success_count} 段，"
        f"翻译成功 {translation_success_count} 段。"
    )
    if fallback_segment_count:
        final_status += f" 失败段数：{fallback_segment_count}，已使用 fallback。"
    final_status += f" {polish_result.status} | {final_translation_result.status}"

    insight_text = _build_meeting_insight(polished_full_source, scene)
    yield polished_full_source, full_translation, _format_status_display(final_status), list(timeline_rows), insight_text


with gr.Blocks(title=APP_TITLE, theme=APP_THEME, css=APP_CSS) as demo:
    gr.HTML(
        """
        <section class="header-bar">
            <div class="header-copy">
                <h1>AI Meeting Interpreter</h1>
                <p>麦克风录制 / 上传会议音频，自动完成 ASR、文本清洗、场景化翻译和双语字幕生成。</p>
            </div>
            <div class="header-chips">
                <span class="chip">Audio Input</span>
                <span class="chip">Local ASR</span>
                <span class="chip">Transcript Polish</span>
                <span class="chip">DeepSeek Translation</span>
                <span class="chip">Bilingual Subtitle</span>
                <span class="chip">AI Meeting Insights</span>
            </div>
        </section>
        """
    )

    with gr.Row(equal_height=True, elem_classes=["workspace-shell"]):
        with gr.Column(scale=3, min_width=320, elem_classes=["left-stack"]):
            with gr.Group(elem_classes=["side-panel"]):
                gr.HTML('<div class="panel-title">音频输入</div>')
                gr.HTML('<div class="panel-subtitle">支持麦克风录制完整语音，或直接上传会议音频文件。</div>')
                stable_audio_input = gr.Audio(
                    label="麦克风录音 / 上传会议音频",
                    sources=["microphone", "upload"],
                    type="filepath",
                )

                gr.HTML('<div class="panel-title" style="margin-top: 12px;">传译配置</div>')
                stable_direction_input = gr.Dropdown(
                    choices=TRANSLATION_DIRECTIONS,
                    value=TRANSLATION_DIRECTIONS[0],
                    label="翻译方向",
                )
                stable_scene_input = gr.Dropdown(
                    choices=MEETING_SCENES,
                    value=MEETING_SCENES[0],
                    label="会议场景",
                )
                stable_mode_input = gr.Dropdown(
                    choices=PROCESSING_MODES,
                    value=PROCESSING_MODES[0],
                    label="处理模式",
                )
                stable_scene_strategy_output = gr.Textbox(
                    label="AI 场景策略",
                    value=_scene_strategy_text(MEETING_SCENES[0]),
                    lines=6,
                    interactive=False,
                    elem_classes=["compact-box", "strategy-box"],
                )
                stable_submit_button = gr.Button(
                    "开始准实时传译",
                    variant="primary",
                    elem_classes=["primary-action"],
                )

        with gr.Column(scale=7, min_width=760, elem_classes=["right-stack"]):
            with gr.Row(equal_height=True, elem_classes=["output-row"]):
                with gr.Column(scale=1):
                    with gr.Group(elem_classes=["content-panel"]):
                        gr.HTML('<div class="panel-title">原文转写</div>')
                        stable_source_output = gr.Textbox(
                            label="原文",
                            lines=10,
                            elem_classes=["compact-box", "output-box"],
                        )

                with gr.Column(scale=1):
                    with gr.Group(elem_classes=["content-panel"]):
                        gr.HTML('<div class="panel-title">译文结果</div>')
                        stable_translated_output = gr.Textbox(
                            label="译文",
                            lines=10,
                            elem_classes=["compact-box", "output-box"],
                        )

            with gr.Group(elem_classes=["tab-panel"]):
                with gr.Tabs():
                    with gr.Tab("🕒 双语字幕时间轴"):
                        stable_timeline_output = gr.Dataframe(
                            headers=["时间段", "原文", "译文", "状态"],
                            datatype=["str", "str", "str", "str"],
                            label="双语字幕时间轴",
                            row_count=(1, "dynamic"),
                            col_count=(4, "fixed"),
                            elem_classes=["timeline-wrap"],
                        )

                    with gr.Tab("🧠 AI 会议理解"):
                        stable_insight_output = gr.Textbox(
                            label="AI 会议理解",
                            lines=11,
                            elem_classes=["compact-box", "insight-box"],
                        )

                    with gr.Tab("⚙️ 系统处理状态"):
                        stable_status_output = gr.Textbox(
                            label="状态",
                            lines=11,
                            elem_classes=["compact-box", "status-box"],
                        )

    stable_submit_button.click(
        fn=run_demo,
        inputs=[stable_audio_input, stable_direction_input, stable_scene_input, stable_mode_input],
        outputs=[
            stable_source_output,
            stable_translated_output,
            stable_status_output,
            stable_timeline_output,
            stable_insight_output,
        ],
    )

    stable_scene_input.change(
        fn=_scene_strategy_text,
        inputs=[stable_scene_input],
        outputs=[stable_scene_strategy_output],
        queue=False,
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=2).launch()
