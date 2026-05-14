"""Atomic JSON persistence for pipeline artifacts (same format as before)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class StorageService:
    def save_json(self, data: dict[str, Any], output_path: str | Path) -> str:
        """Write UTF-8 JSON with indentation via a temp file + replace (crash-safe)."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = output_path.parent / f"{output_path.name}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
            os.replace(tmp_path, output_path)
        except Exception:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            raise
        return str(output_path)

    def load_json(self, input_path: str | Path) -> dict[str, Any]:
        input_path = Path(input_path)
        if not input_path.is_file():
            raise FileNotFoundError(f"JSON not found: {input_path}")
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                out: dict[str, Any] = json.load(f)
            return out
        except json.JSONDecodeError as exc:
            raise json.JSONDecodeError(
                f"{exc.msg} (file: {input_path})",
                exc.doc,
                exc.pos,
            ) from exc
