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

prompt_builder = PromptBuilder()
asr_service = LocalASRService()
translate_service = TranslateService(prompt_builder=prompt_builder)


def run_demo(audio_file: str | None, direction: str, scene: str) -> tuple[str, str, str]:
    if not audio_file:
        return "", "", "请先上传音频文件"

    audio_path = Path(audio_file)
    context = prompt_builder.build(direction=direction, scene=scene, audio_filename=audio_path.name)
    asr_result = asr_service.transcribe(audio_path=str(audio_path), context=context)
    translation_result = translate_service.translate(
        source_text=asr_result.transcript,
        direction=direction,
        meeting_scene=scene,
    )

    status_parts = [asr_result.status, translation_result.status]
    status = " | ".join(part for part in status_parts if part)

    return asr_result.transcript, translation_result.translated_text, status


with gr.Blocks(title=APP_TITLE) as demo:
    gr.Markdown(f"# {APP_TITLE}")
    gr.Markdown("上传音频文件，执行本地语音识别和 DeepSeek 翻译，返回双语字幕结果。")

    with gr.Row():
        audio_input = gr.Audio(label="会议音频", type="filepath")
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
            submit_button = gr.Button("开始处理", variant="primary")

    with gr.Column():
        source_output = gr.Textbox(label="原文", lines=6)
        translated_output = gr.Textbox(label="译文", lines=6)
        status_output = gr.Textbox(label="状态", lines=2)

    submit_button.click(
        fn=run_demo,
        inputs=[audio_input, direction_input, scene_input],
        outputs=[source_output, translated_output, status_output],
    )


if __name__ == "__main__":
    demo.launch()
