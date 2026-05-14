"""PDF meeting report (no Streamlit dependency)."""

from __future__ import annotations

from typing import Any


def build_meeting_pdf_bytes(data: dict[str, Any], report_filename: str) -> bytes:
    """
    Executive \"AI Meeting Intelligence Brief\" — structured, visual, deduplicated.

    Falls back to a tiny error PDF only if the executive builder fails (e.g. matplotlib).
    """
    from pathlib import Path

    from fpdf import FPDF
    from fpdf.enums import WrapMode, XPos, YPos

    def _safe(s: str, limit: int = 800) -> str:
        t = str(s).replace("\r\n", "\n").strip()
        if len(t) > limit:
            t = t[: limit - 3] + "..."
        return t.encode("latin-1", errors="replace").decode("latin-1")

    try:
        from app.frontend.report_pdf_executive import build_executive_meeting_pdf_bytes

        return build_executive_meeting_pdf_bytes(data, report_filename)
    except Exception:
        pdf = FPDF(format="A4", unit="mm")
        pdf.set_margins(14, 14, 14)
        pdf.add_page()
        pdf.set_font("Helvetica", "", 10)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            pdf.epw,
            6,
            _safe(
                "The executive PDF could not be built (charts or layout). "
                f"File: {Path(report_filename).name}. Try Word/Markdown export or check matplotlib/fpdf logs.",
                900,
            ),
            wrapmode=WrapMode.CHAR,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        out = pdf.output()
        if isinstance(out, str):
            return out.encode("latin-1")
        return bytes(out)
