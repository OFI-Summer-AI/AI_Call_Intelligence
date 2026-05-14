"""Diarization detection for pipeline branching (artifacts + meeting intel)."""

from __future__ import annotations

from app.services.pipeline_artifacts import JobArtifactPaths
from app.services.storage_service import StorageService


def has_usable_diarization(
    paths: JobArtifactPaths,
    storage: StorageService,
    stt_backend: str,
) -> bool:
    """
    True when OpenAI diarized STT is active or the diarization artifact has segments.

    Whisper jobs without pyannote (or empty segments file) return False.
    """
    if stt_backend == "openai_diarize":
        return True
    if not paths.diarization.exists():
        return False
    doc = storage.load_json(paths.diarization)
    segs = doc.get("segments") if isinstance(doc, dict) else None
    return bool(segs)
