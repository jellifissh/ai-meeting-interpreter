import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ASRResult:
    transcript: str
    status: str
    used_mock: bool


class MockASRService:
    """Fallback ASR used when local model init or inference is unavailable."""

    _MOCK_TRANSCRIPTS = {
        ("中文→英文", "通用会议"): "各位早上好，今天我们先同步项目进度，再讨论下周的交付安排。",
        ("中文→英文", "技术会议"): "当前版本已经完成接口联调，但我们还需要解决高并发场景下的延迟问题。",
        ("中文→英文", "金融会议"): "本季度营收整体符合预期，但我们需要继续关注现金流和成本控制。",
        ("中文→英文", "面试场景"): "你好，请先简单介绍一下你最近负责的项目，以及你在其中承担的核心职责。",
        ("英文→中文", "通用会议"): "Good morning everyone, let's review the project status first and then align on next week's delivery plan.",
        ("英文→中文", "技术会议"): "The current release has completed API integration, but we still need to reduce latency under high concurrency.",
        ("英文→中文", "金融会议"): "Revenue for this quarter is in line with expectations, but we need to keep watching cash flow and cost control.",
        ("英文→中文", "面试场景"): "Hi, could you briefly introduce the latest project you worked on and explain your core responsibilities?",
    }

    def transcribe(self, audio_path: str, context: dict | None = None) -> ASRResult:
        direction = (context or {}).get("direction", "中文→英文")
        scene = (context or {}).get("scene", "通用会议")
        transcript = self._MOCK_TRANSCRIPTS.get((direction, scene), "未找到匹配的 mock 原文。")
        return ASRResult(
            transcript=transcript,
            status="Local ASR unavailable, fallback to mock ASR.",
            used_mock=True,
        )


class LocalASRService:
    """SenseVoiceSmall-based local ASR with automatic mock fallback."""

    _MODEL_NAME = "SenseVoiceSmall"
    _MODEL_REPO = "iic/SenseVoiceSmall"

    def __init__(self) -> None:
        self.mock_service = MockASRService()
        self.model = None
        self.postprocess = None
        self.init_error: str | None = None
        self.model_dir: Path | None = None
        self.audio_preprocessor = AudioPreprocessor()
        self.initialize()

    def initialize(self) -> None:
        try:
            from funasr import AutoModel
            from funasr.utils.postprocess_utils import rich_transcription_postprocess
        except Exception as exc:
            self.init_error = f"FunASR import failed: {exc}"
            return

        try:
            model_dir = self._prepare_model_dir()
            self.model = AutoModel(
                model=self._MODEL_REPO,
                model_path=str(model_dir),
                device="cpu",
                disable_update=True,
            )
            self.postprocess = rich_transcription_postprocess
            self.model_dir = model_dir
            self.init_error = None
        except Exception as exc:
            self.model = None
            self.postprocess = None
            self.init_error = str(exc)

    def transcribe(self, audio_path: str, context: dict | None = None) -> ASRResult:
        if self.model is None:
            fallback = self.mock_service.transcribe(audio_path=audio_path, context=context)
            status = "Local ASR failed: initialization failed, fallback to mock ASR."
            if self.init_error:
                status = f"Local ASR failed: {self._summarize_error(self.init_error)}, fallback to mock ASR."
            return ASRResult(
                transcript=fallback.transcript,
                status=status,
                used_mock=True,
            )

        try:
            normalized_audio_path = self.audio_preprocessor.convert_to_16k_mono_wav(audio_path)
            result = self.model.generate(
                input=str(normalized_audio_path),
                cache={},
                language="auto",
                use_itn=True,
                batch_size_s=60,
            )
            raw_text = self._extract_text(result)
            transcript = self.postprocess(raw_text).strip() if self.postprocess else raw_text
            transcript = self._maybe_fix_mojibake(transcript)

            if not transcript:
                raise ValueError("Empty ASR transcript.")

            return ASRResult(
                transcript=transcript,
                status="Local ASR success",
                used_mock=False,
            )
        except Exception as exc:
            fallback = self.mock_service.transcribe(audio_path=audio_path, context=context)
            return ASRResult(
                transcript=fallback.transcript,
                status=f"Local ASR failed: {self._summarize_error(exc)}, fallback to mock ASR.",
                used_mock=True,
            )

    def _prepare_model_dir(self) -> Path:
        ascii_cache_dir = Path.cwd() / ".model_cache" / self._MODEL_NAME
        if self._is_ready_model_dir(ascii_cache_dir):
            return ascii_cache_dir

        source_dir = self._find_existing_model_dir()
        if source_dir is None:
            source_dir = self._download_model_dir()

        ascii_cache_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, ascii_cache_dir, dirs_exist_ok=True)
        return ascii_cache_dir

    def _find_existing_model_dir(self) -> Path | None:
        candidates = []

        env_userprofile = os.environ.get("USERPROFILE")
        if env_userprofile:
            candidates.append(Path(env_userprofile) / ".cache" / "modelscope" / "hub" / "models" / "iic" / self._MODEL_NAME)

        shell_userprofile = self._read_powershell_userprofile()
        if shell_userprofile:
            candidates.append(Path(shell_userprofile) / ".cache" / "modelscope" / "hub" / "models" / "iic" / self._MODEL_NAME)

        home_candidate = Path.home() / ".cache" / "modelscope" / "hub" / "models" / "iic" / self._MODEL_NAME
        candidates.append(home_candidate)

        for candidate in candidates:
            if self._is_ready_model_dir(candidate):
                return candidate
        return None

    def _download_model_dir(self) -> Path:
        from modelscope.hub.snapshot_download import snapshot_download

        snapshot_path = snapshot_download(model_id=self._MODEL_REPO)
        candidate = Path(snapshot_path)
        if not self._is_ready_model_dir(candidate):
            raise RuntimeError("Downloaded SenseVoiceSmall model is incomplete.")
        return candidate

    @staticmethod
    def _is_ready_model_dir(model_dir: Path) -> bool:
        required_files = [
            model_dir / "config.yaml",
            model_dir / "model.pt",
            model_dir / "tokens.json",
            model_dir / "chn_jpn_yue_eng_ko_spectok.bpe.model",
            model_dir / "am.mvn",
        ]
        return all(path.exists() for path in required_files)

    @staticmethod
    def _read_powershell_userprofile() -> str | None:
        try:
            import subprocess

            completed = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Write-Output $env:USERPROFILE"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            value = completed.stdout.strip()
            return value or None
        except Exception:
            return None

    @staticmethod
    def _maybe_fix_mojibake(text: str) -> str:
        suspicious_markers = ("å", "æ", "ç", "è", "é", "ã", "â")
        if not text or not any(marker in text for marker in suspicious_markers):
            return text

        try:
            fixed = text.encode("latin1").decode("utf-8")
            return fixed if fixed else text
        except Exception:
            return text

    @staticmethod
    def _summarize_error(exc: Exception | str) -> str:
        message = str(exc).strip().replace("\r", " ").replace("\n", " ")
        return message[:180] if len(message) > 180 else message

    def _extract_text(self, result: object) -> str:
        if isinstance(result, dict):
            return self._extract_text_from_item(result)

        if isinstance(result, list):
            texts = [self._extract_text_from_item(item) for item in result]
            merged = " ".join(text for text in texts if text.strip())
            return merged.strip()

        raise TypeError(f"Unexpected ASR result type: {type(result).__name__}")

    def _extract_text_from_item(self, item: object) -> str:
        if not isinstance(item, dict):
            return str(item).strip()

        if isinstance(item.get("text"), str) and item["text"].strip():
            return item["text"].strip()

        sentence_info = item.get("sentence_info")
        if isinstance(sentence_info, list):
            parts = []
            for sentence in sentence_info:
                if isinstance(sentence, dict):
                    text = str(sentence.get("text", "")).strip()
                    if text:
                        parts.append(text)
            if parts:
                return " ".join(parts).strip()

        if isinstance(item.get("sentence_text"), str) and item["sentence_text"].strip():
            return item["sentence_text"].strip()

        return ""


class AudioPreprocessor:
    """Normalize uploaded audio to a format that local ASR handles reliably."""

    def __init__(self) -> None:
        self.cache_dir = Path.cwd() / "runtime" / "audio_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def convert_to_16k_mono_wav(self, audio_path: str) -> Path:
        source_path = Path(audio_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Audio file not found: {source_path}")

        output_path = self.cache_dir / f"{source_path.stem}_{uuid.uuid4().hex}_16k_mono.wav"
        ffmpeg_path = self._resolve_ffmpeg_path()

        command = [
            str(ffmpeg_path),
            "-y",
            "-i",
            str(source_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(output_path),
        ]

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0 or not output_path.exists():
            stderr = completed.stderr.strip() or completed.stdout.strip() or "ffmpeg conversion failed"
            raise RuntimeError(stderr)

        return output_path

    def _resolve_ffmpeg_path(self) -> Path:
        candidates = [
            Path.cwd() / "runtime" / "ffmpeg" / "ffmpeg.exe",
            Path.cwd() / "runtime" / "ffmpeg" / "bin" / "ffmpeg.exe",
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return Path(system_ffmpeg)

        raise FileNotFoundError(
            "ffmpeg not found. Put ffmpeg.exe under runtime/ffmpeg/ or install ffmpeg in PATH."
        )
