from pathlib import Path
import os
import whisper
from app.services.audio_extractor import _resolve_ffmpeg_binary


class STTService:
    def __init__(self, model_size: str = "base"):
        ffmpeg_binary = _resolve_ffmpeg_binary()
        ffmpeg_bin_dir = str(Path(ffmpeg_binary).parent)
        current_path = os.environ.get("PATH", "")
        if ffmpeg_bin_dir not in current_path:
            os.environ["PATH"] = ffmpeg_bin_dir + os.pathsep + current_path

        self.model = whisper.load_model(model_size)

    def transcribe(self, audio_path: str | Path) -> dict:
        """
        Returns Whisper transcript with timestamps.
        """
        result = self.model.transcribe(str(audio_path), fp16=False)

        segments = []
        for seg in result.get("segments", []):
            segments.append(
                {
                    "start": self._seconds_to_timestamp(seg["start"]),
                    "end": self._seconds_to_timestamp(seg["end"]),
                    "text": seg["text"].strip(),
                }
            )

        return {
            "language": result.get("language"),
            "text": result.get("text", "").strip(),
            "segments": segments,
        }

    @staticmethod
    def _seconds_to_timestamp(seconds: float) -> str:
        total_seconds = int(seconds)
        hh = total_seconds // 3600
        mm = (total_seconds % 3600) // 60
        ss = total_seconds % 60
        return f"{hh:02d}:{mm:02d}:{ss:02d}"