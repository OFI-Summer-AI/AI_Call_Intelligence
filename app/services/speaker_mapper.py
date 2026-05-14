from typing import Any, Dict, List, Optional

_PASSTHROUGH = frozenset(
    {"avg_logprob", "compression_ratio", "no_speech_prob", "temperature", "confidence"}
)


def _time_to_seconds(t: str) -> int:
    hh, mm, ss = t.split(":")
    return int(hh) * 3600 + int(mm) * 60 + int(ss)


def _overlap(seg_start: int, seg_end: int, spk_start: int, spk_end: int) -> int:
    return max(0, min(seg_end, spk_end) - max(seg_start, spk_start))


def assign_speakers_to_transcript(
    transcript_segments: List[Dict],
    diarization_segments: List[Dict],
) -> List[Dict]:
    """
    Assigns a speaker to each Whisper transcript segment based on maximum time overlap.

    Transcript segment example:
      {"start": "00:00:10", "end": "00:00:15", "text": "..."}

    Diarization segment example:
      {"speaker": "Speaker_1", "start": "00:00:09", "end": "00:00:16"}
    """
    merged = []

    for tseg in transcript_segments:
        t_start = _time_to_seconds(tseg["start"])
        t_end = _time_to_seconds(tseg["end"])

        best_speaker: Optional[str] = None
        best_overlap = 0

        for dseg in diarization_segments:
            d_start = _time_to_seconds(dseg["start"])
            d_end = _time_to_seconds(dseg["end"])

            ov = _overlap(t_start, t_end, d_start, d_end)
            if ov > best_overlap:
                best_overlap = ov
                best_speaker = dseg["speaker"]

        row: Dict[str, Any] = {
            "start": tseg["start"],
            "end": tseg["end"],
            "speaker": best_speaker or "Unknown",
            "text": tseg["text"],
        }
        for key in _PASSTHROUGH:
            if key in tseg and tseg[key] is not None:
                row[key] = tseg[key]
        merged.append(row)

    return merged
