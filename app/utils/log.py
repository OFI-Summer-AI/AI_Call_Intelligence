"""
Application logging: one-time setup and short ``stage=`` lines for the pipeline.

Third-party libraries are quieted to WARNING so the terminal shows our flow first.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Mapping

_configured = False

_QUIET_LOGGERS = (
    "httpx",
    "httpcore",
    "openai",
    "urllib3",
    "matplotlib",
)


def configure_logging(level_name: str | None = None) -> None:
    """
    Configure the root logger once (idempotent).

    ``level_name`` defaults to ``app.config.LOG_LEVEL`` when omitted.
    """
    global _configured
    if _configured:
        return

    try:
        from app.config import LOG_LEVEL as default_level
    except ImportError:
        default_level = "INFO"

    raw = (level_name or default_level or "INFO").strip().upper()
    level = getattr(logging, raw, None)
    if not isinstance(level, int):
        level = logging.INFO

    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        h = logging.StreamHandler(sys.stderr)
        h.setLevel(level)
        h.setFormatter(
            logging.Formatter(
                fmt="%(levelname)s [%(name)s] %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        root.addHandler(h)

    for name in _QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Named logger (call after ``configure_logging`` in the entrypoint)."""
    return logging.getLogger(name)


def log_stage(
    logger: logging.Logger,
    *,
    stage: str,
    duration_ms: int,
    step: int | None = None,
    total: int | None = None,
    detail: Mapping[str, Any] | None = None,
) -> None:
    """
    One terminal line per completed pipeline module.

    ``detail`` holds small key=value hints (segment count, flags); never large payloads.
    """
    parts: list[str] = []
    if step is not None and total is not None:
        parts.append(f"flow {step}/{total}")
    parts.append(f"stage={stage}")
    parts.append(f"{duration_ms}ms")
    if detail:
        for k, v in detail.items():
            if v is None or v == "":
                continue
            parts.append(f"{k}={v}")
    logger.info(" | ".join(parts))
