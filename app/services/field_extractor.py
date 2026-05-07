import re
from typing import List, Dict


class FieldExtractor:
    """
    Simple rule-based starter extractor.
    Replace later with an LLM-based extractor if needed.
    """

    CLIENT_NAME_PATTERNS = [
        r"client name is ([^.]+)",
        r"from ([A-Z][A-Za-z0-9&\s]+)",
    ]

    def extract(self, transcript_segments: List[Dict]) -> dict:
        full_text = " ".join(seg["text"] for seg in transcript_segments)

        return {
            "client_name": self._extract_client_name(full_text),
            "client_problem": self._extract_problem(full_text),
            "strict_requirements": self._extract_requirements(full_text),
            "techstack_platform": self._extract_platforms(full_text),
            "timeline": self._extract_timeline(full_text),
            "budget": self._extract_budget(full_text),
            "next_steps": self._extract_next_steps(full_text),
        }

    def _extract_client_name(self, text: str) -> str | None:
        for pattern in self.CLIENT_NAME_PATTERNS:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    def _extract_problem(self, text: str) -> str | None:
        keywords = [
            "problem",
            "pain point",
            "issue",
            "challenge",
            "difficulty",
            "manual",
            "delay",
        ]
        if any(k in text.lower() for k in keywords):
            return "Potential business problem mentioned in call"
        return None

    def _extract_requirements(self, text: str) -> list[str]:
        reqs = []
        patterns = [
            r"must (?:be|support) ([^.]+)",
            r"need ([^.]+)",
            r"require ([^.]+)",
            r"should ([^.]+)",
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, text, flags=re.IGNORECASE):
                value = m.group(1).strip()
                if value and value not in reqs:
                    reqs.append(value)
        return reqs

    def _extract_platforms(self, text: str) -> list[str]:
        platforms = ["SAP", "Power BI", "Tableau", "Salesforce", "AWS", "Azure", "GCP", "Databricks"]
        found = []
        lower = text.lower()
        for p in platforms:
            if p.lower() in lower:
                found.append(p)
        return found

    def _extract_timeline(self, text: str) -> str | None:
        patterns = [
            r"within (\d+\s?(?:days?|weeks?|months?))",
            r"in (\d+\s?(?:days?|weeks?|months?))",
            r"by (\w+\s?\w*)",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    def _extract_budget(self, text: str) -> str | None:
        patterns = [
            r"\$[\d,]+(?:\.\d+)?",
            r"budget of ([^.]+)",
            r"budget is ([^.]+)",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                return (m.group(1) if m.lastindex else m.group(0)).strip()
        return None

    def _extract_next_steps(self, text: str) -> list[str]:
        steps = []
        patterns = [
            r"next step(?:s)?[:\-]?\s*([^.]+)",
            r"we will ([^.]+)",
            r"follow up on ([^.]+)",
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, text, flags=re.IGNORECASE):
                value = m.group(1).strip()
                if value and value not in steps:
                    steps.append(value)
        return steps