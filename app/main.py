from pathlib import Path
from app.config import UPLOAD_DIR
from app.orchestrator.pipeline import Pipeline
from app.services.audio_extractor import _resolve_ffmpeg_binary


def main():
    ffmpeg_binary = _resolve_ffmpeg_binary()
    print(f"Using FFmpeg: {ffmpeg_binary}")

    # Replace this file name with your actual MP4 file
    mp4_file = UPLOAD_DIR / "client_call_01.mp4"

    if not mp4_file.exists():
        raise FileNotFoundError(f"File not found: {mp4_file}")

    pipeline = Pipeline()
    result = pipeline.run(str(mp4_file))

    print("\nPipeline completed successfully.\n")
    print(result)


if __name__ == "__main__":
    main()