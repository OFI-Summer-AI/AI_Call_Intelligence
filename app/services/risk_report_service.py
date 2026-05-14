from typing import Dict, List


class RiskReportService:
    def generate(self, extracted_fields: Dict, transcript_segments: List[Dict]) -> dict:
        risks = []

        if not extracted_fields.get("client_name"):
            risks.append("Client name was not clearly captured.")

        if not extracted_fields.get("client_problem"):
            risks.append("Client problem is not clearly stated.")

        if not extracted_fields.get("strict_requirements"):
            risks.append("Strict requirements need confirmation.")

        if not extracted_fields.get("techstack_platform"):
            risks.append("Tech stack / platform should be double-checked.")

        if not extracted_fields.get("timeline"):
            risks.append("Timeline was not clearly committed.")

        if not extracted_fields.get("budget"):
            risks.append("Budget was not clearly discussed.")

        if not extracted_fields.get("next_steps"):
            risks.append("Next steps are missing or unclear.")

        return {
            "risks": risks,
            "needs_review": len(risks) > 0,
        }
