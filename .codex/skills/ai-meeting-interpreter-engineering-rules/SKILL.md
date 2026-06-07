---
name: ai-meeting-interpreter-engineering-rules
description: Guardrails for developing the AI Meeting Interpreter Demo under a 48-hour deadline. Use when planning, implementing, validating, or committing work in this project so development stays demo-first, fallback-safe, and split into clear incremental commits that satisfy internship submission requirements.
---

# AI Meeting Interpreter Engineering Rules

## Overview

Treat this project as a 48-hour demo build. Optimize for a runnable handoff first: upload audio, run local ASR, call DeepSeek translation, and show bilingual subtitles. Avoid production-grade detours until the demo path is stable.

## Delivery Order

Follow this sequence:

1. Run the simplest workable path end to end.
2. Stabilize failures with fallbacks.
3. Improve packaging and documentation last.

Do not pre-optimize architecture, performance, concurrency, or deployment.

## Priority Rules

Keep scope aligned to these levels:

- `P0`: runnable page, audio upload, local ASR, DeepSeek translation, bilingual subtitle output, fallback behavior
- `P1`: audio preprocessing, transcript cleanup, terminology injection, stronger prompts
- `P2`: WebSocket, realtime streaming, microphone capture, VAD, GPU optimization, multithreading, Docker, user accounts, databases

If time is tight, protect `P0` and defer everything else.

## Git Workflow

Develop incrementally. One commit should represent one feature or one narrow fix.

Before every commit:

1. Run the relevant validation.
2. Prepare a short change note for the user.
3. Commit only the files for that feature.

Always report:

- changed files
- feature added or fixed
- implementation reason
- validation method

Use specific commit messages such as:

- `feat: initialize Gradio MVP skeleton`
- `feat: add mock ASR service`
- `feat: integrate DeepSeek translation`
- `feat: add translation fallback strategy`
- `feat: integrate local SenseVoiceSmall ASR`
- `fix: improve local ASR initialization handling`
- `docs: update README for local setup`

Do not use vague messages like `update`, `modify`, `fix bug`, or `misc changes`.

## Runtime Safety

Keep `python app.py` runnable after every commit.

All AI-related capabilities must degrade safely:

- ASR initialization failure -> fallback to mock ASR
- ASR transcription failure -> fallback transcript or mock ASR result
- DeepSeek failure -> fallback to mock translation

The page must not crash because of ASR or translation errors.

## Debugging Boundary

When you encounter shell garbling, Unicode console noise, or non-critical logging issues, decide based on the Gradio app, not the terminal.

If the page works and the demo path is intact, stop digging unless the issue blocks `P0`.

This project is a deliverable demo, not a production system.

## README Rule

Write README updates after the core feature works.

Keep README concise and make sure it covers:

- dependencies
- third-party libraries
- fallback behavior
- current limitations
- next steps

Do not spend time polishing documentation before the demo path is working.
