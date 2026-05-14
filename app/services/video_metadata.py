"""
Container-level video metadata via ffprobe (no re-encode).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict


def _resolve_ffprobe_binary() -> str | None:
    import os

    env_value = os.getenv("FFPROBE_PATH", "").strip()
    if env_value:
        p = Path(env_value)
        if p.exists():
            return str(p)
    return shutil.which("ffprobe") or shutil.which("ffprobe.exe")


def probe_video_metadata(video_path: str | Path) -> Dict[str, Any]:
    """
    Return a compact dict suitable for JSON export (duration, resolution, codecs).

    If ffprobe is missing or fails, returns ``{"error": "..."}`` without raising.
    """
    video_path = Path(video_path)
    out: Dict[str, Any] = {"source_path": str(video_path)}
    if not video_path.exists():
        out["error"] = "file_not_found"
        return out

    binary = _resolve_ffprobe_binary()
    if not binary:
        out["error"] = "ffprobe_not_found"
        return out

    cmd = [
        binary,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, OSError) as e:
        out["error"] = f"ffprobe_failed: {e}"
        return out

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[:2000]
        out["error"] = f"ffprobe_exit_{proc.returncode}"
        if err:
            out["ffprobe_stderr"] = err
        return out

    try:
        root = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as e:
        out["error"] = f"ffprobe_json_invalid: {e}"
        return out

    fmt = root.get("format") if isinstance(root, dict) else None
    streams = root.get("streams") if isinstance(root, dict) else None
    if not isinstance(fmt, dict):
        fmt = {}
    if not isinstance(streams, list):
        streams = []

    video_streams = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "audio"]
    vs = video_streams[0] if video_streams else {}

    def _frac_fps(rate: str | None) -> str | None:
        if not rate or rate == "0/0":
            return None
        if "/" in str(rate):
            a, b = str(rate).split("/", 1)
            try:
                af, bf = float(a), float(b)
                if bf:
                    return f"{(af / bf):.3f}".rstrip("0").rstrip(".")
            except (ValueError, ZeroDivisionError):
                pass
        return str(rate)

    duration = fmt.get("duration")
    size = fmt.get("size")
    bit_rate = fmt.get("bit_rate")

    def _opt_float(x: Any) -> float | None:
        if x in (None, ""):
            return None
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    def _opt_int(x: Any) -> int | None:
        if x in (None, ""):
            return None
        try:
            return int(x)
        except (TypeError, ValueError):
            return None

    compact: Dict[str, Any] = {
        "format_name": fmt.get("format_name"),
        "duration_seconds": _opt_float(duration),
        "file_size_bytes": _opt_int(size),
        "container_bit_rate": _opt_int(bit_rate),
    }

    if isinstance(vs, dict) and vs:
        compact["video"] = {
            "codec": vs.get("codec_name"),
            "width": vs.get("width"),
            "height": vs.get("height"),
            "pix_fmt": vs.get("pix_fmt"),
            "avg_frame_rate": _frac_fps(vs.get("avg_frame_rate")),
            "r_frame_rate": _frac_fps(vs.get("r_frame_rate")),
        }

    if audio_streams:
        a0 = audio_streams[0]
        if isinstance(a0, dict):
            compact["audio"] = {
                "codec": a0.get("codec_name"),
                "sample_rate": a0.get("sample_rate"),
                "channels": a0.get("channels"),
            }

    compact["stream_counts"] = {
        "video": len(video_streams),
        "audio": len(audio_streams),
    }

    return compact
