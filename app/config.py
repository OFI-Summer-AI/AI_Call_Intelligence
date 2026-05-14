"""
Central configuration loaded from environment variables (and optional `.env`).

Never commit secrets. Use `.env` locally (gitignored) or your host's secret store.
"""

from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
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

# --- FFmpeg (optional) ---
# Set ``FFMPEG_PATH`` in ``.env`` to the full ``ffmpeg`` / ``ffmpeg.exe`` path.

# --- Speech-to-text ---
STT_BACKEND = os.getenv("STT_BACKEND", "whisper").strip().lower()
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
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.80"))

# --- Logging (CLI / pipeline flow) ---
# DEBUG shows more detail; INFO is the default flow (stage lines only).
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()
