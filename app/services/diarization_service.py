from pathlib import Path
from pyannote.audio import Pipeline
from app.config import DIARIZATION_HF_TOKEN


class DiarizationService:
    def __init__(self):
        if not DIARIZATION_HF_TOKEN:
            raise ValueError("DIARIZATION_HF_TOKEN is missing in environment variables.")
        self.pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=DIARIZATION_HF_TOKEN,
        )

    def diarize(self, audio_path: str | Path) -> list[dict]:
        """
        Returns speaker segments like:
        Speaker_0, Speaker_1 with timestamps.
        """
        diarization = self.pipeline(str(audio_path))
        segments = []

        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(
                {
                    "speaker": speaker,
                    "start": self._seconds_to_timestamp(turn.start),
                    "end": self._seconds_to_timestamp(turn.end),
                }
            )

        return segments

    @staticmethod
    def _seconds_to_timestamp(seconds: float) -> str:
        total_seconds = int(seconds)
        hh = total_seconds // 3600
        mm = (total_seconds % 3600) // 60
        ss = total_seconds % 60
        return f"{hh:02d}:{mm:02d}:{ss:02d}"