from typing import Any, Dict, List

# Optional STT diagnostics preserved for the raw evidence layer (Whisper).
_PASSTHROUGH_NUMERIC = frozenset(
    {"avg_logprob", "compression_ratio", "no_speech_prob", "temperature"}
)


def clean_segments(segments: List[Dict]) -> List[Dict]:
    """
    Light cleanup:
    - trim spaces
    - remove empty segments
    - preserve optional confidence-related fields when present
    """
    cleaned: List[Dict[str, Any]] = []
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        row: Dict[str, Any] = {
            "start": seg["start"],
            "end": seg["end"],
            "text": " ".join(text.split()),
        }
        if "speaker" in seg and seg["speaker"] is not None:
            row["speaker"] = seg["speaker"]
        for key in _PASSTHROUGH_NUMERIC:
            if key in seg and seg[key] is not None:
                try:
                    row[key] = float(seg[key])
                except (TypeError, ValueError):
                    row[key] = seg[key]
        if seg.get("confidence") is not None:
            row["confidence"] = seg["confidence"]
        cleaned.append(row)
    return cleaned
