from pathlib import Path
import os
import subprocess
import shutil


def _resolve_ffmpeg_binary() -> str:
    """
    Resolve ffmpeg executable from env override or PATH.
    """
    env_value = os.getenv("FFMPEG_PATH", "").strip()
    if env_value:
        candidate = Path(env_value)
        if candidate.exists():
            return str(candidate)
        raise RuntimeError(
            f"FFMPEG_PATH is set but does not exist: {env_value}"
        )

    binary = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if binary:
        return binary

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

    audio_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_binary = _resolve_ffmpeg_binary()

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

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Audio extraction failed.\n"
            f"Command: {' '.join(cmd)}\n"
            f"stderr: {result.stderr}"
        )

    return str(audio_path)