"""
Discover user media under uploads and resolve CLI / env inputs.

Extensions align with the Streamlit uploader plus common container formats.
"""

from __future__ import annotations

import os
from pathlib import Path

# Video / audio we can feed to ffmpeg → WAV (see ``audio_extractor``).
MEDIA_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".mp4",
        ".mov",
        ".m4v",
        ".mkv",
        ".webm",
        ".avi",
        ".wmv",
        ".flv",
        ".mpeg",
        ".mpg",
        ".wav",
        ".mp3",
        ".m4a",
        ".aac",
        ".flac",
        ".ogg",
        ".opus",
    }
)


def is_media_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS


def list_media_in_dir(directory: Path) -> list[Path]:
    """Newest files first (mtime), stable for ``--latest``."""
    if not directory.is_dir():
        return []
    items = [p for p in directory.iterdir() if is_media_file(p)]
    items.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return items


def resolve_input_from_env(upload_dir: Path) -> Path | None:
    for key in ("PIPELINE_INPUT", "VIDEO_PATH", "CALL_MEDIA_PATH"):
        raw = os.getenv(key, "").strip().strip('"').strip("'")
        if not raw:
            continue
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = (upload_dir / p).resolve()
        else:
            p = p.resolve()
        if p.is_file() and is_media_file(p):
            return p
        if p.is_file():
            raise ValueError(
                f"{key}={raw!r} is not a supported media type "
                f"(extension must be one of: {', '.join(sorted(MEDIA_EXTENSIONS))})."
            )
        raise FileNotFoundError(f"{key} points to a missing file: {p}")
    return None
