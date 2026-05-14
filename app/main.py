from pathlib import Path

from app.config import OUTPUT_DIR, UPLOAD_DIR
from app.orchestrator.pipeline import Pipeline
from app.utils.log import configure_logging, get_logger


def main() -> None:
    configure_logging()
    log = get_logger(__name__)

    # Replace this file name with your actual MP4 file.
    mp4_file = UPLOAD_DIR / "client_call_01.mp4"

    if not mp4_file.exists():
        raise FileNotFoundError(f"File not found: {mp4_file}")

    log.info("start | input=%s", mp4_file)

    # FFmpeg is resolved inside ``extract_audio`` (cached). Whisper loads lazily
    # on first transcribe when STT_BACKEND=whisper — no heavy import at startup.
    pipeline = Pipeline()
    result = pipeline.run(str(mp4_file))

    ap = result.get("artifact_paths") or {}
    transcript_path = OUTPUT_DIR / f"{result.get('meeting_id', mp4_file.stem)}_transcript.json"
    log.info(
        "done | meeting_id=%s | final_report=%s | transcript=%s | polished_md=%s",
        result.get("meeting_id"),
        ap.get("final_report"),
        transcript_path.as_posix(),
        ap.get("polished_md"),
    )


if __name__ == "__main__":
    main()
