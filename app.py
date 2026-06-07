from pathlib import Path
import re
import uuid
from difflib import SequenceMatcher

import gradio as gr
import numpy as np
import soundfile as sf
from dotenv import load_dotenv

from services.asr_service import LocalASRService
from services.prompt_builder import PromptBuilder
from services.translate_service import TranslateService


load_dotenv()


APP_TITLE = "AI Meeting Interpreter Demo"
TRANSLATION_DIRECTIONS = ["中文→英文", "英文→中文"]
MEETING_SCENES = ["通用会议", "技术会议", "金融会议", "面试场景"]
PROCESSING_MODES = ["分段字幕（推荐）", "整段翻译"]
DEFAULT_SEGMENT_DURATION_SECONDS = 8
MIC_STREAM_EVERY_SECONDS = 4
MIC_STREAM_TIME_LIMIT_SECONDS = 60
MIC_STREAM_CHUNK_DIR = Path.cwd() / "runtime" / "mic_stream_chunks"
MIC_INVALID_CHUNK_THRESHOLD = 3
MIC_SIMILARITY_THRESHOLD = 0.85

prompt_builder = PromptBuilder()
asr_service = LocalASRService()
translate_service = TranslateService(prompt_builder=prompt_builder)
MIC_STREAM_CHUNK_DIR.mkdir(parents=True, exist_ok=True)


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
    merged = re.sub(r"([。！？!?])\s+", r"\1", merged)
    merged = re.sub(r"\s+([,.;:，。！？；：])", r"\1", merged)
    return merged


def _clean_chunk_text(text: str) -> str:
    cleaned = text.replace("\r", " ").replace("\n", " ")
    cleaned = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([,.;:，。！？；：])", r"\1", cleaned)
    return cleaned


def _build_recent_context(source_parts: list[str], limit: int = 2) -> str | None:
    recent_parts = [part for part in source_parts[-limit:] if part]
    if not recent_parts:
        return None
    return _clean_full_transcript(recent_parts)


def _save_stream_chunk(audio_chunk: tuple[int, np.ndarray] | list[object] | None) -> Path | None:
    if not audio_chunk or len(audio_chunk) != 2:
        return None

    sample_rate, audio_array = audio_chunk
    if not sample_rate or audio_array is None:
        return None

    audio_np = np.asarray(audio_array)
    if audio_np.size == 0:
        return None

    output_path = MIC_STREAM_CHUNK_DIR / f"mic_chunk_{uuid.uuid4().hex}.wav"
    sf.write(str(output_path), audio_np, int(sample_rate))
    return output_path


def _format_realtime_rows(rows: list[list[str]]) -> list[list[str]]:
    return [list(row) for row in rows]


def _reset_realtime_state():
    return [], "正在监听麦克风...", [], "", 0, 0


def _count_cjk_chars(text: str) -> int:
    return sum(1 for char in text if "\u4e00" <= char <= "\u9fff")


def _count_english_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text))


def _is_realtime_chunk_too_short(text: str) -> bool:
    return _count_cjk_chars(text) < 5 and _count_english_words(text) < 5


def _is_similar_realtime_transcript(current_text: str, previous_text: str) -> bool:
    if not current_text or not previous_text:
        return False
    similarity = SequenceMatcher(None, current_text.lower(), previous_text.lower()).ratio()
    return similarity >= MIC_SIMILARITY_THRESHOLD


def _build_realtime_idle_status(invalid_chunk_streak: int, default_status: str) -> str:
    if invalid_chunk_streak >= MIC_INVALID_CHUNK_THRESHOLD:
        return "未检测到新的有效语音片段，请尝试说 5-10 秒短句，或使用稳定模式处理完整音频。"
    return default_status


def _skip_realtime_chunk(
    rows: list[list[str]],
    previous_transcript: str,
    current_counter: int,
    invalid_chunk_streak: int,
    default_status: str,
):
    next_invalid_streak = invalid_chunk_streak + 1
    status = _build_realtime_idle_status(next_invalid_streak, default_status)
    return _format_realtime_rows(rows), status, rows, previous_transcript, current_counter, next_invalid_streak


def process_streaming_chunk(
    audio_chunk: tuple[int, np.ndarray] | list[object] | None,
    direction: str,
    scene: str,
    subtitle_rows: list[list[str]] | None,
    last_transcript: str | None,
    counter: int | None,
    invalid_chunk_streak: int | None,
):
    rows = list(subtitle_rows or [])
    previous_transcript = (last_transcript or "").strip()
    current_counter = int(counter or 0)
    current_invalid_streak = int(invalid_chunk_streak or 0)

    if audio_chunk is None:
        return (
            _format_realtime_rows(rows),
            _build_realtime_idle_status(current_invalid_streak, "正在监听麦克风..."),
            rows,
            previous_transcript,
            current_counter,
            current_invalid_streak,
        )

    try:
        chunk_path = _save_stream_chunk(audio_chunk)
        if chunk_path is None:
            return _skip_realtime_chunk(
                rows,
                previous_transcript,
                current_counter,
                current_invalid_streak,
                "正在监听麦克风...",
            )
    except Exception as exc:
        return (
            _format_realtime_rows(rows),
            f"音频 chunk 保存失败：{exc}",
            rows,
            previous_transcript,
            current_counter,
            current_invalid_streak,
        )

    context = prompt_builder.build(direction=direction, scene=scene, audio_filename=chunk_path.name)
    asr_result = asr_service.transcribe(audio_path=str(chunk_path), context=context)
    cleaned_transcript = _clean_chunk_text(asr_result.transcript)

    if not cleaned_transcript:
        return _skip_realtime_chunk(
            rows,
            previous_transcript,
            current_counter,
            current_invalid_streak,
            "ASR transcript 为空，已跳过。",
        )

    if _is_realtime_chunk_too_short(cleaned_transcript):
        return _skip_realtime_chunk(
            rows,
            previous_transcript,
            current_counter,
            current_invalid_streak,
            f"识别文本过短，已跳过：{cleaned_transcript}",
        )

    if cleaned_transcript == previous_transcript:
        return _skip_realtime_chunk(
            rows,
            previous_transcript,
            current_counter,
            current_invalid_streak,
            "检测到重复 transcript，已跳过。",
        )

    if previous_transcript and cleaned_transcript in previous_transcript:
        return _skip_realtime_chunk(
            rows,
            previous_transcript,
            current_counter,
            current_invalid_streak,
            "检测到子串级重复 transcript，已跳过。",
        )

    if _is_similar_realtime_transcript(cleaned_transcript, previous_transcript):
        return _skip_realtime_chunk(
            rows,
            previous_transcript,
            current_counter,
            current_invalid_streak,
            "检测到高相似 transcript，已跳过。",
        )

    translation_result = translate_service.translate(
        source_text=cleaned_transcript,
        direction=direction,
        meeting_scene=scene,
        context_text=previous_transcript or None,
    )
    cleaned_translation = _clean_chunk_text(translation_result.translated_text)

    current_counter += 1
    row_status_parts = [part for part in [asr_result.status, translation_result.status] if part]
    row_status = " | ".join(row_status_parts)
    rows.append([str(current_counter), cleaned_transcript, cleaned_translation, row_status])

    status = f"已追加第 {current_counter} 条字幕。"
    if asr_result.used_mock:
        status += f" {asr_result.status}"
    elif translation_result.used_mock:
        status += f" {translation_result.status}"

    return _format_realtime_rows(rows), status, rows, cleaned_transcript, current_counter, 0


def _run_full_audio_demo(
    audio_path: Path,
    context: dict,
    direction: str,
    scene: str,
) -> tuple[str, str, str, list[list[str]]]:
    asr_result = asr_service.transcribe(audio_path=str(audio_path), context=context)
    translation_result = translate_service.translate(
        source_text=asr_result.transcript,
        direction=direction,
        meeting_scene=scene,
    )

    status_parts = [asr_result.status, translation_result.status]
    status = " | ".join(part for part in status_parts if part)
    timeline_rows = [["整段", asr_result.transcript, translation_result.translated_text, status]]

    return asr_result.transcript, translation_result.translated_text, status, timeline_rows


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

    total_segments = len(segments)
    yield "", "", f"正在处理：第 0 / {total_segments} 段，ASR 成功 0 段，翻译成功 0 段。", []

    for index, segment in enumerate(segments, start=1):
        segment_context = dict(context)
        asr_result = asr_service.transcribe(audio_path=segment.audio_path, context=segment_context)
        cleaned_source_text = _clean_chunk_text(asr_result.transcript)
        recent_context = _build_recent_context(source_parts)
        translation_result = translate_service.translate(
            source_text=cleaned_source_text,
            direction=direction,
            meeting_scene=scene,
            context_text=recent_context,
        )
        cleaned_translated_text = _clean_chunk_text(translation_result.translated_text)

        combined_status = " | ".join(
            part for part in [segment.status, asr_result.status, translation_result.status] if part
        )
        source_parts.append(cleaned_source_text)
        translated_parts.append(cleaned_translated_text)

        if not asr_result.used_mock and "success" in asr_result.status.lower():
            asr_success_count += 1

        if not translation_result.used_mock and translation_result.status == "处理成功":
            translation_success_count += 1

        if asr_result.used_mock or translation_result.used_mock:
            fallback_segment_count += 1

        timeline_rows.append(
            [
                f"{segment.start_time} - {segment.end_time}",
                cleaned_source_text,
                cleaned_translated_text,
                combined_status,
            ]
        )

        cumulative_source = _clean_full_transcript(source_parts)
        cumulative_translation = _clean_full_transcript(translated_parts)
        progress_status = (
            f"正在处理：第 {index} / {total_segments} 段，"
            f"ASR 成功 {asr_success_count} 段，"
            f"翻译成功 {translation_success_count} 段。"
        )

        yield cumulative_source, cumulative_translation, progress_status, list(timeline_rows)

    full_source = _clean_full_transcript(source_parts)
    full_translation = _clean_full_transcript(translated_parts)

    final_status = (
        f"处理完成：共 {total_segments} 段，"
        f"ASR 成功 {asr_success_count} 段，"
        f"翻译成功 {translation_success_count} 段。"
    )
    if fallback_segment_count:
        final_status += f" 失败段数：{fallback_segment_count}，已使用 fallback。"

    yield (
        full_source,
        full_translation,
        final_status,
        list(timeline_rows),
    )


with gr.Blocks(title=APP_TITLE) as demo:
    gr.Markdown(f"# {APP_TITLE}")
    gr.Markdown(
        "AI Pipeline: Local ASR(SenseVoiceSmall/FunASR) -> DeepSeek LLM Translation -> Bilingual Subtitle Timeline"
    )
    with gr.Tabs():
        with gr.Tab("上传/录制式准实时传译（稳定）"):
            gr.Markdown(
                "当前版本为上传/录制式准实时同传 Demo：用户可录制完整会议音频或直接上传音频，系统会将音频切分为短片段，逐段进行本地 ASR 和 DeepSeek 翻译，并动态生成双语字幕时间轴。"
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

        with gr.Tab("麦克风短句实时传译（实验）"):
            gr.Markdown(
                "该模式适合 5-10 秒短句演示。系统会尝试对麦克风音频 chunk 进行 ASR 和翻译，并追加字幕。长音频或完整会议请使用稳定模式。"
            )

            realtime_subtitle_state = gr.State([])
            realtime_last_transcript_state = gr.State("")
            realtime_counter_state = gr.State(0)
            realtime_invalid_chunk_state = gr.State(0)

            with gr.Row():
                realtime_audio_input = gr.Audio(
                    label="实时麦克风输入",
                    sources=["microphone"],
                    type="numpy",
                    streaming=True,
                )
                with gr.Column():
                    realtime_direction_input = gr.Dropdown(
                        choices=TRANSLATION_DIRECTIONS,
                        value=TRANSLATION_DIRECTIONS[0],
                        label="翻译方向",
                    )
                    realtime_scene_input = gr.Dropdown(
                        choices=MEETING_SCENES,
                        value=MEETING_SCENES[0],
                        label="会议场景",
                    )
                    realtime_clear_button = gr.Button("清空字幕")

            realtime_status_output = gr.Textbox(label="状态", value="正在监听麦克风...", lines=3)
            realtime_timeline_output = gr.Dataframe(
                headers=["序号", "原文", "译文", "状态"],
                datatype=["str", "str", "str", "str"],
                label="实时字幕",
                row_count=(1, "dynamic"),
                col_count=(4, "fixed"),
            )

            realtime_audio_input.stream(
                fn=process_streaming_chunk,
                inputs=[
                    realtime_audio_input,
                    realtime_direction_input,
                    realtime_scene_input,
                    realtime_subtitle_state,
                    realtime_last_transcript_state,
                    realtime_counter_state,
                    realtime_invalid_chunk_state,
                ],
                outputs=[
                    realtime_timeline_output,
                    realtime_status_output,
                    realtime_subtitle_state,
                    realtime_last_transcript_state,
                    realtime_counter_state,
                    realtime_invalid_chunk_state,
                ],
                stream_every=MIC_STREAM_EVERY_SECONDS,
                time_limit=MIC_STREAM_TIME_LIMIT_SECONDS,
                show_progress="hidden",
                concurrency_limit=1,
            )

            realtime_clear_button.click(
                fn=_reset_realtime_state,
                inputs=[],
                outputs=[
                    realtime_timeline_output,
                    realtime_status_output,
                    realtime_subtitle_state,
                    realtime_last_transcript_state,
                    realtime_counter_state,
                    realtime_invalid_chunk_state,
                ],
                queue=False,
            )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=2).launch()
