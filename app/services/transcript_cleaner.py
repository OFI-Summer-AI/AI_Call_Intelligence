from typing import List, Dict


def clean_segments(segments: List[Dict]) -> List[Dict]:
    """
    Light cleanup:
    - trim spaces
    - remove empty segments
    """
    cleaned = []
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        cleaned.append(
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": " ".join(text.split()),
            }
        )
    return cleaned