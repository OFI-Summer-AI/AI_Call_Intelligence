"""
Command-line entry for batch / single-file pipeline runs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import PIPELINE_RESUME, UPLOAD_DIR
from app.core.media_inputs import MEDIA_EXTENSIONS, list_media_in_dir, resolve_input_from_env
from app.orchestrator.pipeline import Pipeline
from app.utils.log import configure_logging, get_logger


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run call-intelligence pipeline on a video or audio file (ffmpeg, STT, reports)."
    )
    p.add_argument(
        "input",
        nargs="?",
        help="Path to a media file. If omitted, use env PIPELINE_INPUT / VIDEO_PATH or --latest in uploads.",
    )
    p.add_argument(
        "--upload-dir",
        type=Path,
        default=UPLOAD_DIR,
        help=f"Folder scanned for --latest / --all (default: {UPLOAD_DIR}).",
    )
    pick = p.add_mutually_exclusive_group()
    pick.add_argument(
        "--latest",
        action="store_true",
        help="Explicitly pick the newest file in --upload-dir (same as omitting input when env is unset).",
    )
    pick.add_argument(
        "--all",
        action="store_true",
        help="Process every supported file in --upload-dir (newest first). Continues on errors.",
    )
    p.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=PIPELINE_RESUME,
        help=f"Resume from artifacts when possible (default from env PIPELINE_RESUME: {PIPELINE_RESUME}).",
    )
    return p


def _resolve_single_input(args: argparse.Namespace, log) -> Path:
    upload_dir: Path = args.upload_dir.expanduser().resolve()

    if args.input:
        path = Path(args.input).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Not a file: {path}")
        if path.suffix.lower() not in MEDIA_EXTENSIONS:
            raise ValueError(
                f"Unsupported extension {path.suffix!r}. Supported: {', '.join(sorted(MEDIA_EXTENSIONS))}"
            )
        return path

    env_path = resolve_input_from_env(upload_dir)
    if env_path is not None:
        log.info("using env input | path=%s", env_path)
        return env_path

    candidates = list_media_in_dir(upload_dir)
    if not candidates:
        raise FileNotFoundError(
            f"No supported media in {upload_dir}. "
            f"Extensions: {', '.join(sorted(MEDIA_EXTENSIONS))}. "
            "Drop a file in uploads, pass a path, or set PIPELINE_INPUT."
        )

    chosen = candidates[0]
    log.info("picked latest upload | path=%s", chosen)
    return chosen


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    log = get_logger(__name__)
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.input and args.all:
        parser.error("Cannot combine a positional input path with --all.")

    upload_dir: Path = args.upload_dir.expanduser().resolve()
    if not upload_dir.is_dir():
        log.error("upload dir does not exist: %s", upload_dir)
        return 2

    pipeline = Pipeline()
    failures: list[tuple[str, str]] = []

    def run_one(media: Path, resume: bool) -> None:
        log.info("start | input=%s | resume=%s", media, resume)
        result = pipeline.run(str(media), resume=resume)
        ap = result.get("artifact_paths") or {}
        log.info(
            "done | meeting_id=%s | final_report=%s | polished_md=%s",
            result.get("meeting_id"),
            ap.get("final_report"),
            ap.get("polished_md"),
        )

    if args.all:
        files = list_media_in_dir(upload_dir)
        if not files:
            log.error("No media files in %s", upload_dir)
            return 1
        log.info("batch | count=%s | upload_dir=%s", len(files), upload_dir)
        for media in files:
            try:
                run_one(media, args.resume)
            except Exception as exc:  # noqa: BLE001
                log.exception("failed | input=%s | err=%s", media, exc)
                failures.append((str(media), str(exc)))
        if failures:
            log.error("batch finished with %s failure(s)", len(failures))
            for path, err in failures:
                log.error("  %s -> %s", path, err)
            return 1
        return 0

    try:
        target = _resolve_single_input(args, log)
    except (FileNotFoundError, ValueError) as exc:
        log.error("%s", exc)
        return 1

    try:
        run_one(target, args.resume)
    except Exception:  # noqa: BLE001
        log.exception("failed | input=%s", target)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
