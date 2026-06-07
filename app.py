from pathlib import Path
import re

import gradio as gr
from dotenv import load_dotenv

from services.asr_service import LocalASRService
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

prompt_builder = PromptBuilder()
asr_service = LocalASRService()
transcript_polish_service = TranscriptPolishService()
translate_service = TranslateService(prompt_builder=prompt_builder)


def run_demo(
    audio_file: str | None,
    direction: str,
    scene: str,
    processing_mode: str,
):
    if not audio_file:
        yield "", "", "请先录制或上传音频", []
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


def _run_full_audio_demo(
    audio_path: Path,
    context: dict,
    direction: str,
    scene: str,
) -> tuple[str, str, str, list[list[str]]]:
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
    status = " | ".join(part for part in status_parts if part)
    timeline_rows = [["整段", asr_result.transcript, translation_result.translated_text, status]]

    return polished_transcript, translation_result.translated_text, status, timeline_rows


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
        full_source, full_translation, full_status, timeline_rows = _run_full_audio_demo(
            audio_path,
            context,
            direction,
            scene,
        )
        fallback_status = f"Segmented subtitle mode failed: {exc}. Fallback to full-audio mode. | {full_status}"
        yield full_source, full_translation, fallback_status, timeline_rows
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
    yield "", "", f"正在处理：第 0 / {total_segments} 段，ASR 成功 0 段，翻译成功 0 段。", []

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

        yield cumulative_source, cumulative_translation, progress_status, list(timeline_rows)

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

    yield polished_full_source, full_translation, final_status, list(timeline_rows)


with gr.Blocks(title=APP_TITLE) as demo:
    gr.Markdown(f"# {APP_TITLE}")
    gr.Markdown(
        "AI Pipeline: Local ASR(SenseVoiceSmall/FunASR) -> Transcript Polish -> DeepSeek LLM Translation -> Bilingual Subtitle Timeline"
    )

    with gr.Tabs():
        with gr.Tab("上传/录制式准实时传译（稳定）"):
            gr.Markdown(
                "当前版本为上传/录制式准实时同传 Demo：用户可录制完整会议音频或直接上传音频，系统会将音频切分为短片段，逐段进行本地 ASR、Transcript Polish 和 DeepSeek 翻译，并动态生成双语字幕时间轴。"
            )

            with gr.Row():
                stable_audio_input = gr.Audio(
                    label="麦克风录音 / 上传会议音频",
                    sources=["microphone", "upload"],
                    type="filepath",
                )
                with gr.Column():
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
                    stable_submit_button = gr.Button("开始准实时传译", variant="primary")

            with gr.Column():
                stable_source_output = gr.Textbox(label="原文", lines=6)
                stable_translated_output = gr.Textbox(label="译文", lines=6)
                stable_status_output = gr.Textbox(label="状态", lines=3)
                stable_timeline_output = gr.Dataframe(
                    headers=["时间段", "原文", "译文", "状态"],
                    datatype=["str", "str", "str", "str"],
                    label="双语字幕时间轴",
                    row_count=(1, "dynamic"),
                    col_count=(4, "fixed"),
                )

            stable_submit_button.click(
                fn=run_demo,
                inputs=[stable_audio_input, stable_direction_input, stable_scene_input, stable_mode_input],
                outputs=[
                    stable_source_output,
                    stable_translated_output,
                    stable_status_output,
                    stable_timeline_output,
                ],
            )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=2).launch()
