import json
import re
from typing import List, Dict

from openai import OpenAI

from app.config import LLM_MODEL, OPENAI_API_KEY


class FieldExtractor:
    """
    LLM-based sales field extraction from speaker-attributed transcript segments.
    Falls back to a minimal structure if OPENAI_API_KEY is missing or JSON parse fails.
    """

    def __init__(self) -> None:
        self._api_key = OPENAI_API_KEY
        self._model = LLM_MODEL
        self._client: OpenAI | None = OpenAI(api_key=self._api_key) if self._api_key else None

    def extract(self, transcript_segments: List[Dict]) -> dict:
        if not self._client:
            return self._empty_extraction(
                "OPENAI_API_KEY is not set; skipping LLM extraction."
            )

        transcript_text = self._build_transcript_text(transcript_segments)

        prompt = f"""
You are a sales call intelligence extractor.

From the transcript below, extract these fields:
- client_name
- client_problem
- strict_requirements
- techstack_platform
- budget
- timeline
- next_steps
- risks

Rules:
- Return ONLY valid JSON (no markdown fences).
- If a field is not clearly present, use null or empty list.
- Keep the output concise and factual.
- Do not invent information.

Transcript:
{transcript_text}
"""

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": "You extract structured sales intelligence from meeting transcripts.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

        raw = (response.choices[0].message.content or "").strip()
        raw = self._strip_json_fence(raw)

        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        return {
            "client_name": None,
            "client_problem": None,
            "strict_requirements": [],
            "techstack_platform": [],
            "budget": None,
            "timeline": None,
            "next_steps": [],
            "risks": [],
            "raw_llm_output": raw,
        }

    def _empty_extraction(self, note: str) -> dict:
        return {
            "client_name": None,
            "client_problem": None,
            "strict_requirements": [],
            "techstack_platform": [],
            "budget": None,
            "timeline": None,
            "next_steps": [],
            "risks": [],
            "extraction_note": note,
        }

    @staticmethod
    def _strip_json_fence(raw: str) -> str:
        m = re.match(r"^\s*```(?:json)?\s*\n?(.*?)\n?```\s*$", raw, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else raw

    def _build_transcript_text(self, transcript_segments: List[Dict]) -> str:
        lines = []
        for seg in transcript_segments:
            speaker = seg.get("speaker", "Unknown")
            start = seg.get("start", "")
            text = seg.get("text", "")
            lines.append(f"[{start}] {speaker}: {text}")
        return "\n".join(lines)
