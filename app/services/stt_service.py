from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.services.audio_extractor import _resolve_ffmpeg_binary


class STTService:
    """
    Local Whisper STT. Whisper and the model are loaded lazily on the first
    ``transcribe`` call so importing ``Pipeline`` / ``STTService`` does not pay
    the PyTorch + weight load cost (often mistaken for "ffmpeg startup").
    """

    def __init__(self, model_size: str = "base") -> None:
        self._model_size = model_size
        self._model: Any = None
        self._ffmpeg_path_ready = False

    def _ensure_ffmpeg_on_path(self) -> None:
        if self._ffmpeg_path_ready:
            return
        ffmpeg_binary = _resolve_ffmpeg_binary()
        ffmpeg_bin_dir = str(Path(ffmpeg_binary).parent)
        current_path = os.environ.get("PATH", "")
        if ffmpeg_bin_dir not in current_path:
            os.environ["PATH"] = ffmpeg_bin_dir + os.pathsep + current_path
        self._ffmpeg_path_ready = True

    def _get_model(self) -> Any:
        if self._model is None:
            import whisper

            self._ensure_ffmpeg_on_path()
            self._model = whisper.load_model(self._model_size)
        return self._model

    def transcribe(self, audio_path: str | Path) -> dict:
        """
        Returns Whisper transcript with timestamps.
        """
        self._ensure_ffmpeg_on_path()
        model = self._get_model()

        # fp16=False keeps CPU execution compatible on most developer machines.
        result = model.transcribe(str(audio_path), fp16=False)

        # Normalize Whisper segments to project-wide schema.
        segments = []
        for seg in result.get("segments", []):
            row: dict[str, Any] = {
                "start": self._seconds_to_timestamp(self._seg_seconds(seg, "start")),
                "end": self._seconds_to_timestamp(self._seg_seconds(seg, "end")),
                "text": self._seg_text(seg).strip(),
            }
            for key in ("avg_logprob", "compression_ratio", "no_speech_prob", "temperature"):
                v = self._seg_optional_float(seg, key)
                if v is not None:
                    row[key] = v
            segments.append(row)

        return {
            "language": result.get("language"),
            "text": result.get("text", "").strip(),
            "segments": segments,
        }

    @staticmethod
    def _seg_seconds(seg: Any, key: str) -> float:
        if isinstance(seg, dict):
            return float(seg.get(key, 0.0))
        return float(getattr(seg, key, 0.0))

    @staticmethod
    def _seg_text(seg: Any) -> str:
        if isinstance(seg, dict):
            return str(seg.get("text") or "")
        return str(getattr(seg, "text", "") or "")

    @staticmethod
    def _seg_optional_float(seg: Any, key: str) -> float | None:
        if isinstance(seg, dict):
            v = seg.get(key)
        else:
            v = getattr(seg, key, None)
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _seconds_to_timestamp(seconds: float) -> str:
        total_seconds = int(seconds)
        hh = total_seconds // 3600
        mm = (total_seconds % 3600) // 60
        ss = total_seconds % 60
        return f"{hh:02d}:{mm:02d}:{ss:02d}"
