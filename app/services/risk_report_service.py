from typing import Dict, List


class RiskReportService:
    def generate(self, extracted_fields: Dict, transcript_segments: List[Dict]) -> dict:
        risks = []

        if not extracted_fields.get("client_name"):
            risks.append("Client name not clearly identified.")

        if not extracted_fields.get("client_problem"):
            risks.append("Client problem/pain point not clearly captured.")

        if not extracted_fields.get("strict_requirements"):
            risks.append("Strict requirements should be double-checked with client.")

        if not extracted_fields.get("techstack_platform"):
            risks.append("Tech stack / platform not clearly mentioned.")

        if not extracted_fields.get("timeline"):
            risks.append("Timeline not clearly committed.")

        if not extracted_fields.get("budget"):
            risks.append("Budget not clearly confirmed.")

        if not extracted_fields.get("next_steps"):
            risks.append("Next steps should be confirmed.")

        return {
            "risks": risks,
            "needs_review": len(risks) > 0,
        }