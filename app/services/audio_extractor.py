from pathlib import Path
import os
import subprocess
import shutil

# Resolve once per process; repeated extract/transcribe calls should not re-scan PATH.
_cached_ffmpeg: str | None = None


def _resolve_ffmpeg_binary() -> str:
    """
    Resolve ffmpeg executable from env override or PATH.

    For faster, predictable startup on machines with very large PATH, set
    ``FFMPEG_PATH`` to the full ``ffmpeg`` / ``ffmpeg.exe`` path so we skip
    ``shutil.which`` scanning.
    """
    global _cached_ffmpeg
    if _cached_ffmpeg is not None:
        return _cached_ffmpeg

    # Allow explicit override when ffmpeg is not globally available on PATH.
    env_value = os.getenv("FFMPEG_PATH", "").strip()
    if env_value:
        candidate = Path(env_value)
        if candidate.exists():
            _cached_ffmpeg = str(candidate)
            return _cached_ffmpeg
        raise RuntimeError(
            f"FFMPEG_PATH is set but does not exist: {env_value}"
        )

    # Fallback to shell PATH lookup.
    binary = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if binary:
        _cached_ffmpeg = binary
        return _cached_ffmpeg

    raise RuntimeError(
        "ffmpeg executable not found. Install FFmpeg and add it to PATH, "
        "or set FFMPEG_PATH to the full ffmpeg executable path."
    )


def extract_audio(video_path: str | Path, audio_path: str | Path) -> str:
    """
    Convert MP4 to WAV audio.
    """
    video_path = Path(video_path)
    audio_path = Path(audio_path)

    # Ensure output directory exists before running ffmpeg.
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_binary = _resolve_ffmpeg_binary()

    # Convert input video to mono 16kHz WAV for consistent STT behavior.
    cmd = [
        ffmpeg_binary,
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path),
    ]

    # Capture stderr to surface actionable ffmpeg diagnostics on failure.
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Audio extraction failed.\n"
            f"Command: {' '.join(cmd)}\n"
            f"stderr: {result.stderr}"
        )

    return str(audio_path)