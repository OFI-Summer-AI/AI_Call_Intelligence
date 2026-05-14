"""
Speech-to-text + speaker diarization via OpenAI (no Hugging Face / pyannote).

Uses ``gpt-4o-transcribe-diarize`` with ``diarized_json``. See:
https://developers.openai.com/api/docs/guides/speech-to-text

Notes:
- Audio upload limit is 25 MB per request.
- For inputs longer than 30 seconds, ``chunking_strategy`` is required (we use ``auto``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Dict

from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_TRANSCRIBE_MODEL


def _seconds_to_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)
    hh = total_seconds // 3600
    mm = (total_seconds % 3600) // 60
    ss = total_seconds % 60
    return f"{hh:02d}:{mm:02d}:{ss:02d}"


class OpenAIDiarizedSTTService:
    """Transcribe audio with per-segment speaker labels using OpenAI's diarized model."""

    def __init__(self) -> None:
        if not OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is required for STT_BACKEND=openai_diarize. "
                "Set it in .env or switch STT_BACKEND=whisper."
            )
        self._client = OpenAI(api_key=OPENAI_API_KEY)
        self._model = OPENAI_TRANSCRIBE_MODEL

    def transcribe(self, audio_path: str | Path) -> dict:
        """
        Returns the same top-level shape as ``STTService``:
        ``language``, ``text``, ``segments`` — each segment includes ``speaker``.
        """
        audio_path = Path(audio_path)
        with open(audio_path, "rb") as audio_file:
            transcript = self._client.audio.transcriptions.create(
                model=self._model,
                file=audio_file,
                response_format="diarized_json",
                chunking_strategy="auto",
            )

        raw_segments = _get_segments_list(transcript)
        segments: List[Dict[str, Any]] = []
        for seg in raw_segments:
            start_s = _coerce_seconds(seg, "start")
            end_s = _coerce_seconds(seg, "end")
            text = (getattr(seg, "text", None) if not isinstance(seg, dict) else seg.get("text")) or ""
            text = str(text).strip()
            spk = getattr(seg, "speaker", None) if not isinstance(seg, dict) else seg.get("speaker")
            if not text:
                continue
            segments.append(
                {
                    "start": _seconds_to_timestamp(start_s),
                    "end": _seconds_to_timestamp(end_s),
                    "speaker": str(spk) if spk is not None else "Unknown",
                    "text": " ".join(text.split()),
                }
            )

        full_text = " ".join(s["text"] for s in segments)
        language = getattr(transcript, "language", None)
        if language is None and isinstance(transcript, dict):
            language = transcript.get("language")

        return {
            "language": language,
            "text": full_text.strip(),
            "segments": segments,
        }


def _get_segments_list(transcript: Any) -> list:
    if hasattr(transcript, "segments") and transcript.segments is not None:
        return list(transcript.segments)
    if isinstance(transcript, dict) and "segments" in transcript:
        return list(transcript["segments"])
    return []


def _coerce_seconds(seg: Any, key: str) -> float:
    if isinstance(seg, dict):
        v = seg.get(key, 0.0)
    else:
        v = getattr(seg, key, 0.0)
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0
