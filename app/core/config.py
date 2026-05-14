"""
Central configuration loaded from environment variables (and optional `.env`).

Never commit secrets. Use `.env` locally (gitignored) or your host's secret store.
"""

from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()

# --- Paths (repo root is two levels above this file: app/core/config.py) ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
AUDIO_DIR = DATA_DIR / "audio"
# Legacy single-folder outputs (still created; Streamlit falls back here if no final reports).
OUTPUT_DIR = DATA_DIR / "outputs"

# Production-style artifact layout (one stage → one file under ``data/``).
TRANSCRIPTS_RAW_DIR = DATA_DIR / "transcripts" / "raw"
TRANSCRIPTS_MERGED_DIR = DATA_DIR / "transcripts" / "merged"
TRANSCRIPTS_ROLE_MAPPED_DIR = DATA_DIR / "transcripts" / "role_mapped"
DIARIZATION_DIR = DATA_DIR / "diarization"
POLISHED_DIR = DATA_DIR / "polished"
EXTRACTED_DIR = DATA_DIR / "extracted"
REPORTS_DIR = DATA_DIR / "reports"
REPORTS_FINAL_DIR = DATA_DIR / "reports" / "final"
METADATA_DIR = DATA_DIR / "metadata"
LOGS_DIR = DATA_DIR / "logs"

_ARTIFACT_DIRS = (
    UPLOAD_DIR,
    AUDIO_DIR,
    OUTPUT_DIR,
    TRANSCRIPTS_RAW_DIR,
    TRANSCRIPTS_MERGED_DIR,
    TRANSCRIPTS_ROLE_MAPPED_DIR,
    DIARIZATION_DIR,
    POLISHED_DIR,
    EXTRACTED_DIR,
    REPORTS_DIR,
    REPORTS_FINAL_DIR,
    METADATA_DIR,
    LOGS_DIR,
)
for folder in _ARTIFACT_DIRS:
    folder.mkdir(parents=True, exist_ok=True)

# --- Streamlit uploads (megabytes; keep in sync with .streamlit/config.toml [server] maxUploadSize) ---
def _env_int(name: str, default: int, *, min_v: int, max_v: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        v = int(str(raw).strip(), 10)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer (got {raw!r})") from exc
    if v < min_v:
        raise ValueError(f"{name} must be >= {min_v} (got {v})")
    if max_v is not None and v > max_v:
        raise ValueError(f"{name} must be <= {max_v} (got {v})")
    return v


STREAMLIT_MAX_UPLOAD_MB = _env_int("STREAMLIT_MAX_UPLOAD_MB", 8192, min_v=1, max_v=1024 * 1024)

# --- FFmpeg (optional) ---
# Set ``FFMPEG_PATH`` in ``.env`` to the full ``ffmpeg`` / ``ffmpeg.exe`` path.

# --- Speech-to-text ---
STT_BACKEND = os.getenv("STT_BACKEND", "whisper").strip().lower()
_STT_ALLOWED = frozenset({"whisper", "openai_diarize"})
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
OPENAI_TRANSCRIBE_MODEL = os.getenv(
    "OPENAI_TRANSCRIBE_MODEL", "gpt-4o-transcribe-diarize"
).strip()

# --- OpenAI (LLM) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# --- Hugging Face (pyannote) ---
DIARIZATION_HF_TOKEN = os.getenv("DIARIZATION_HF_TOKEN", "").strip()
ENABLE_DIARIZATION = os.getenv("ENABLE_DIARIZATION", "false").lower() == "true"

# --- Pipeline ---
# When true, reuse existing on-disk artifacts to skip expensive stages (see ``Pipeline.run``).
PIPELINE_RESUME = os.getenv("PIPELINE_RESUME", "false").lower() in ("1", "true", "yes")
PIPELINE_VERSION = os.getenv("PIPELINE_VERSION", "2.1").strip()

# --- Other ---
def _env_float(name: str, default: float, *, min_v: float, max_v: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        v = float(str(raw).strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a number (got {raw!r})") from exc
    if not (min_v <= v <= max_v):
        raise ValueError(f"{name} must be between {min_v} and {max_v} inclusive (got {v})")
    return v


CONFIDENCE_THRESHOLD = _env_float("CONFIDENCE_THRESHOLD", 0.80, min_v=0.0, max_v=1.0)

# --- Logging (CLI / pipeline flow) ---
# DEBUG shows more detail; INFO is the default flow (stage lines only).
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()
_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


def _validate_config() -> None:
    """Fail fast on unsafe or mistyped environment (does not change artifact layout)."""
    if STT_BACKEND not in _STT_ALLOWED:
        raise ValueError(f"STT_BACKEND must be one of {sorted(_STT_ALLOWED)}, got {STT_BACKEND!r}")
    if LOG_LEVEL not in _LOG_LEVELS:
        raise ValueError(f"LOG_LEVEL must be one of {sorted(_LOG_LEVELS)}, got {LOG_LEVEL!r}")


_validate_config()
