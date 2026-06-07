from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

from services.asr_service import LocalASRService
from services.prompt_builder import PromptBuilder
from services.translate_service import TranslateService


load_dotenv()


APP_TITLE = "AI Meeting Interpreter Demo"
TRANSLATION_DIRECTIONS = ["中文→英文", "英文→中文"]
MEETING_SCENES = ["通用会议", "技术会议", "金融会议", "面试场景"]
PROCESSING_MODES = ["分段字幕（推荐）", "整段翻译"]

prompt_builder = PromptBuilder()
asr_service = LocalASRService()
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
        segments = asr_service.segment_audio(str(audio_path), segment_duration_seconds=5)
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
    translation_parts: list[str] = []
    status_parts: list[str] = []

    yield "", "", "分段字幕模式已启动，正在逐段处理中...", []

    for index, segment in enumerate(segments, start=1):
        segment_context = dict(context)
        asr_result = asr_service.transcribe(audio_path=segment.audio_path, context=segment_context)
        translation_result = translate_service.translate(
            source_text=asr_result.transcript,
            direction=direction,
            meeting_scene=scene,
        )

        combined_status = " | ".join(
            part for part in [segment.status, asr_result.status, translation_result.status] if part
        )
        source_parts.append(asr_result.transcript)
        translation_parts.append(translation_result.translated_text)
        status_parts.append(combined_status)

        timeline_rows.append(
            [
                f"{segment.start_time} - {segment.end_time}",
                asr_result.transcript,
                translation_result.translated_text,
                combined_status,
            ]
        )

        full_source = "\n".join(part for part in source_parts if part.strip())
        full_translation = "\n".join(part for part in translation_parts if part.strip())
        progress_status = f"Segmented subtitle mode running ({index}/{len(segments)}) | {combined_status}"

        yield full_source, full_translation, progress_status, list(timeline_rows)

    final_status = "Segmented subtitle mode completed"
    if status_parts:
        final_status = f"{final_status} | {' | '.join(status_parts)}"

    yield (
        "\n".join(part for part in source_parts if part.strip()),
        "\n".join(part for part in translation_parts if part.strip()),
        final_status,
        list(timeline_rows),
    )


with gr.Blocks(title=APP_TITLE) as demo:
    gr.Markdown(f"# {APP_TITLE}")
    gr.Markdown(
        "当前版本为麦克风录制式准实时同传 Demo：用户可录制或上传会议音频，系统会将音频切分为短片段，逐段进行本地 ASR 和 DeepSeek 翻译，并动态生成双语字幕时间轴。"
    )
    gr.Markdown(
        "AI Pipeline: Local ASR(SenseVoiceSmall/FunASR) -> DeepSeek LLM Translation -> Bilingual Subtitle Timeline"
    )

    with gr.Row():
        audio_input = gr.Audio(
            label="麦克风录音 / 上传会议音频",
            sources=["microphone", "upload"],
            type="filepath",
        )
        with gr.Column():
            direction_input = gr.Dropdown(
                choices=TRANSLATION_DIRECTIONS,
                value=TRANSLATION_DIRECTIONS[0],
                label="翻译方向",
            )
            scene_input = gr.Dropdown(
                choices=MEETING_SCENES,
                value=MEETING_SCENES[0],
                label="会议场景",
            )
            mode_input = gr.Dropdown(
                choices=PROCESSING_MODES,
                value=PROCESSING_MODES[0],
                label="处理模式",
            )
            submit_button = gr.Button("开始准实时传译", variant="primary")

    with gr.Column():
        source_output = gr.Textbox(label="原文", lines=6)
        translated_output = gr.Textbox(label="译文", lines=6)
        status_output = gr.Textbox(label="状态", lines=3)
        timeline_output = gr.Dataframe(
            headers=["时间段", "原文", "译文", "状态"],
            datatype=["str", "str", "str", "str"],
            label="双语字幕时间轴",
            row_count=(1, "dynamic"),
            col_count=(4, "fixed"),
        )

    submit_button.click(
        fn=run_demo,
        inputs=[audio_input, direction_input, scene_input, mode_input],
        outputs=[source_output, translated_output, status_output, timeline_output],
    )


if __name__ == "__main__":
    demo.launch()
