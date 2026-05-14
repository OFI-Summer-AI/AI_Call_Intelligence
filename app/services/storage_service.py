from pathlib import Path
import json


class StorageService:
    def save_json(self, data: dict, output_path: str | Path) -> str:
        # Normalize path input and ensure parent folders exist.
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Persist UTF-8 JSON with indentation for readability/debugging.
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Return saved location for caller logging/chaining.
        return str(output_path)

    def load_json(self, input_path: str | Path) -> dict:
        input_path = Path(input_path)
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)