"""
Executive \"AI Meeting Intelligence Brief\" PDF — premium layout, tables, smarter charts.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from fpdf import FPDF
from fpdf.enums import WrapMode, XPos, YPos

from app.frontend.chart_helpers import distinct_speakers
from app.frontend.meeting_registry import get_entry, meeting_id_from_report_filename
from app.frontend.report_artifacts import job_paths_for_report, merged_risk_view
from app.frontend.report_pdf_figures import build_intelligence_pngs
from app.frontend.report_pdf_intel import (
    cq_conclusion_text,
    cq_insights_list,
    filtered_insights,
    merge_next_steps,
    missing_discussion_areas,
    narrative_opening,
    smart_quote_highlights,
    strategic_assessment_bullets,
    tactical_client_signals,
    topic_importance_matrix,
)
from app.frontend.report_pdf_narrative import (
    compliance_mentions,
    decision_clarity_label,
    engagement_label,
    executive_bullets,
    format_duration_hms,
    guess_meeting_datetime,
    budget_label,
    pain_points_from_polished,
    parse_polished_list,
    recommendation_banner_text,
    risk_severity_prefix,
)

_LOGO_PATH = Path(__file__).resolve().parent / "assets" / "ofi_logo.png"
_OFI_GOLD = (230, 197, 103)
_OFI_GOLD_DARK = (212, 175, 55)
_OFI_BLACK = (0, 0, 0)
_OFI_YELLOW_FILLS = (
    (255, 249, 219),
    (255, 243, 196),
    (255, 236, 179),
    (255, 248, 225),
    (255, 253, 231),
    (255, 249, 219),
)


def _latin1(text: str, limit: int = 12_000) -> str:
    t = str(text).replace("\r\n", "\n").strip()
    if len(t) > limit:
        t = t[: limit - 3] + "..."
    return t.encode("latin-1", errors="replace").decode("latin-1")


def _title_display(report_filename: str, data: dict[str, Any]) -> str:
    mid = meeting_id_from_report_filename(report_filename)
    meta = get_entry(mid)
    if meta.get("display_title"):
        return str(meta["display_title"])
    return str(data.get("meeting_id") or mid).replace("_", " ")[:120]


class _BriefPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*_OFI_GOLD_DARK)
        self.cell(0, 8, _latin1(f"OFI Call Intelligence · Page {self.page_no()}", 60), align="C")


def _maybe_new_page(pdf: FPDF, min_y: float) -> None:
    if pdf.get_y() > min_y:
        pdf.add_page()


def _image_row(pdf: FPDF, png: bytes, *, max_h_mm: float = 76.0) -> None:
    _maybe_new_page(pdf, 235)
    y0 = pdf.get_y()
    pdf.image(io.BytesIO(png), x=pdf.l_margin, y=y0, w=pdf.epw, h=max_h_mm)
    pdf.set_y(y0 + max_h_mm + 8)


def _hero_bar(pdf: FPDF) -> None:
    y = pdf.get_y()
    bar_h = 14.0
    pdf.set_fill_color(*_OFI_BLACK)
    pdf.rect(pdf.l_margin, y, pdf.epw, bar_h, style="F")
    text_x = pdf.l_margin + 3
    if _LOGO_PATH.is_file():
        logo_w = 11.0
        pdf.image(str(_LOGO_PATH), x=pdf.l_margin + 2, y=y + 1.5, w=logo_w, h=logo_w)
        text_x = pdf.l_margin + logo_w + 4
    pdf.set_xy(text_x, y + 4.2)
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.set_text_color(*_OFI_GOLD)
    pdf.cell(0, 5, _latin1("OFI Call Intelligence", 80))
    pdf.set_text_color(*_OFI_BLACK)
    pdf.set_y(y + bar_h + 2)


def _heading(pdf: FPDF, text: str, *, size: int = 13, rgb: tuple[int, int, int] = _OFI_GOLD_DARK) -> None:
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", size)
    pdf.set_text_color(*rgb)
    pdf.multi_cell(pdf.epw, 7.5, _latin1(text, 200), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1.5)


def _subheading(pdf: FPDF, text: str) -> None:
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*_OFI_BLACK)
    pdf.multi_cell(pdf.epw, 6, _latin1(text, 160), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)


def _body(pdf: FPDF, text: str, *, h: float = 5.6, limit: int = 6000) -> None:
    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        pdf.epw,
        h,
        _latin1(text, limit),
        wrapmode=WrapMode.WORD,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )


def _kpi_table(pdf: FPDF, rows: list[tuple[str, str]]) -> None:
    w_label = pdf.epw * 0.52
    w_val = pdf.epw * 0.48
    row_h = 9.0
    for i, (lab, val) in enumerate(rows):
        rgb = _OFI_YELLOW_FILLS[i % len(_OFI_YELLOW_FILLS)]
        pdf.set_fill_color(*rgb)
        pdf.set_draw_color(*_OFI_GOLD_DARK)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_OFI_BLACK)
        pdf.cell(w_label, row_h, _latin1(lab, 72), border=1, fill=True)
        pdf.set_font("Helvetica", "", 10.5)
        pdf.cell(w_val, row_h, _latin1(val, 96), border=1, ln=1, fill=True)
    pdf.ln(2)


def _banner(pdf: FPDF, text: str) -> None:
    pdf.ln(4)
    y = pdf.get_y()
    pdf.set_fill_color(255, 249, 219)
    pdf.set_draw_color(*_OFI_GOLD_DARK)
    pdf.rect(pdf.l_margin, y, pdf.epw, 20, style="DF")
    pdf.set_xy(pdf.l_margin + 3, y + 4)
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.set_text_color(*_OFI_BLACK)
    pdf.multi_cell(pdf.epw - 6, 6.2, _latin1(text, 520), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_y(y + 22)


def _trunc_cell(s: str, max_chars: int) -> str:
    t = str(s).strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1] + "."


def _data_table(pdf: FPDF, headers: list[str], rows: list[tuple[str, ...]], col_widths: list[float]) -> None:
    hdr_h = 8.0
    row_h = 8.0
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*_OFI_GOLD)
    pdf.set_text_color(*_OFI_BLACK)
    pdf.set_draw_color(*_OFI_GOLD_DARK)
    for h, w in zip(headers, col_widths):
        pdf.cell(w, hdr_h, _latin1(_trunc_cell(h, int(w / 1.45)), 100), border=1, fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for row in rows:
        for cell, w in zip(row, col_widths):
            mc = max(24, int(w / 1.2) + 12)
            pdf.cell(w, row_h, _latin1(_trunc_cell(str(cell), mc), 800), border=1)
        pdf.ln()
    pdf.ln(2)


def _discovery_blocks_pdf(pdf: FPDF, cov: list[Any], *, max_items: int = 12) -> None:
    """Readable checklist: one block per question (avoids truncated table cells)."""
    rows_in = [r for r in cov if isinstance(r, dict)]
    if not rows_in:
        _body(pdf, "No discovery checklist rows in this export.", limit=400)
        return
    _body(
        pdf,
        "Each block is one checklist question from your pipeline, with capture status, model notes, and evidence. "
        "Full rows remain in the product JSON export.",
        limit=420,
    )
    pdf.ln(3)
    for i, row in enumerate(rows_in[:max_items]):
        q = str(row.get("title", row.get("id", "?"))).strip()
        st = str(row.get("status", "")).replace("_", " ").strip().title()
        conf = str(row.get("confidence", "")).strip().title()
        status_line = f"{st} ({conf})" if conf else st
        notes = str(row.get("notes", "") or "").strip() or "—"
        ev = str(row.get("evidence", "") or "").strip() or "—"
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*_OFI_GOLD_DARK)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            pdf.epw,
            6.5,
            _latin1(q, 1400),
            wrapmode=WrapMode.WORD,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 10)
        block = f"Status: {status_line}\n\nNotes\n{notes}\n\nEvidence\n{ev}"
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            pdf.epw,
            5.6,
            _latin1(block, 5200),
            wrapmode=WrapMode.WORD,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.ln(6 if i < min(len(rows_in), max_items) - 1 else 3)
    if len(rows_in) > max_items:
        pdf.set_font("Helvetica", "I", 9.5)
        pdf.set_text_color(*_OFI_BLACK)
        pdf.multi_cell(
            pdf.epw,
            5.5,
            _latin1(
                f"… {len(rows_in) - max_items} more checklist rows in the product export.",
                220,
            ),
            wrapmode=WrapMode.WORD,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.set_text_color(0, 0, 0)


def _actions_rich_table(pdf: FPDF, actions: list[str]) -> None:
    headers = ["Action", "Owner", "Urgency", "Status"]
    w = [pdf.epw * 0.48, pdf.epw * 0.18, pdf.epw * 0.17, pdf.epw * 0.17]
    rows: list[tuple[str, str, str, str]] = []
    for i, act in enumerate(actions[:12]):
        urg = "High" if i < 2 else "Medium"
        rows.append((act, "TBD (assign in CRM)", urg, "Pending"))
    _data_table(pdf, headers, rows, w)


def build_executive_meeting_pdf_bytes(data: dict[str, Any], report_filename: str) -> bytes:
    paths = job_paths_for_report(report_filename)
    risk = merged_risk_view(data, paths)
    ef = data.get("extracted_fields") or {}
    cq = data.get("call_quality_report") or {}
    pt = data.get("polished_transcript") or {}
    if not isinstance(pt, dict):
        pt = {}
    transcript = data.get("transcript") or []
    topics = data.get("topic_wise_summary") or []
    cov = data.get("question_coverage") if isinstance(data.get("question_coverage"), list) else []

    title = _title_display(report_filename, data)
    meeting_id = str(data.get("meeting_id") or meeting_id_from_report_filename(report_filename))
    client = str(ef.get("client_name") or "—")
    when = guess_meeting_datetime(meeting_id)
    duration = format_duration_hms(data)
    participants = distinct_speakers(transcript)
    src = str(data.get("source_file") or "")
    meeting_type = "Uploaded recording" if "upload" in src.lower() else "Recording"

    eff = cq.get("conformance_score_0_100")
    if isinstance(eff, (int, float)):
        eff_s = f"{int(round(float(eff)))}%"
    else:
        conf = cq.get("conformance") or {}
        sc = conf.get("score_0_100") if isinstance(conf, dict) else None
        eff_s = f"{int(sc)}%" if isinstance(sc, (int, float)) else "—"

    actions = cq.get("next_actions") or []
    if not isinstance(actions, list):
        actions = []
    actions = [str(a).strip() for a in actions if str(a).strip()]
    rlist = list(risk.get("risks") or [])
    if isinstance(rlist, list):
        rlist = [str(x).strip() for x in rlist if str(x).strip()]

    merged_steps = merge_next_steps(actions, pt)
    insights_list = cq_insights_list(cq)
    concl_text = cq_conclusion_text(cq)
    pending_areas = missing_discussion_areas(cov)
    ind_raw = cq.get("individual_assessment") or []
    ind_list = [x for x in ind_raw if isinstance(x, dict)] if isinstance(ind_raw, list) else []
    ind_n = len(ind_list)
    participant_tile = str(ind_n) if ind_n else ("Needs speaker IDs" if not data.get("has_diarization") else "0")
    n_themes = len(topics) if isinstance(topics, list) else 0
    total_q = cq.get("questions_total")
    if not isinstance(total_q, (int, float)) and isinstance(cov, list):
        total_q = len(cov)
    checklist_s = str(int(total_q)) if isinstance(total_q, (int, float)) and int(total_q) > 0 else "—"

    matrix_rows = topic_importance_matrix(topics if isinstance(topics, list) else [], transcript)
    pngs = build_intelligence_pngs(data)

    pdf = _BriefPDF(format="A4", unit="mm")
    pdf.set_margins(16, 16, 16)
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.add_page()
    _hero_bar(pdf)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*_OFI_BLACK)
    pdf.multi_cell(pdf.epw, 8, _latin1("Executive AI Meeting Intelligence Brief", 120))
    pdf.set_font("Helvetica", "B", 11.5)
    pdf.set_text_color(*_OFI_GOLD_DARK)
    pdf.multi_cell(pdf.epw, 6.5, _latin1(title, 200))
    pdf.set_text_color(0, 0, 0)
    meta_lines = [
        f"Client: {client}",
        f"Reference time (from file name): {when}",
        f"Duration: {duration}",
        f"Distinct speaker labels: {participants if participants else '—'}",
        f"Meeting type: {meeting_type}",
    ]
    _body(pdf, "\n".join(meta_lines), limit=800)

    _heading(pdf, "Executive snapshot", size=12)
    _kpi_table(
        pdf,
        [
            ("Meeting effectiveness (checklist)", eff_s),
            ("Engagement (tone proxy)", engagement_label(data)),
            ("Action items captured (merged)", str(len(merged_steps))),
            ("Risks / watch-outs", str(len(rlist))),
            ("Budget discussed", budget_label(ef, cq)),
            ("Decision clarity (proxy)", decision_clarity_label(cq)),
        ],
    )
    _subheading(pdf, "Signal counts (matches product dashboard header)")
    _kpi_table(
        pdf,
        [
            ("Insights on call", str(len(insights_list))),
            ("Next actions (merged list)", str(len(merged_steps))),
            ("Participant scorecards", participant_tile),
            ("Open discovery gaps", str(len(pending_areas))),
            ("Watch-out flags", str(len(rlist))),
            ("Theme groups", str(n_themes)),
            ("Checklist questions", checklist_s),
        ],
    )

    _subheading(pdf, "What happened (one narrative)")
    _body(pdf, narrative_opening(pt, str(data.get("summary") or "")), limit=1100)

    _heading(pdf, "Executive bullets", size=11)
    bullets = executive_bullets(str(data.get("summary") or ""), max_n=5)
    if bullets:
        for b in bullets:
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(
                pdf.epw,
                5.6,
                _latin1(f"- {b}", 600),
                wrapmode=WrapMode.WORD,
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            pdf.ln(1.5)
    else:
        _body(pdf, "(No packaged summary.)")

    _banner(pdf, recommendation_banner_text(cq))

    # --- Visual intelligence ---
    pdf.add_page()
    _heading(pdf, "Meeting intelligence (visual)", size=12)
    _body(
        pdf,
        "Speaker heatmap (who was active over time), sentiment proxy, momentum by meeting segment, "
        "and topic depth (relative, from model topic summaries).",
        limit=420,
    )
    _image_row(pdf, pngs["speaker_timeline"], max_h_mm=48)
    _image_row(pdf, pngs["sentiment"], max_h_mm=38)
    pdf.add_page()
    _image_row(pdf, pngs["momentum"], max_h_mm=34)
    _image_row(pdf, pngs["topic_depth"], max_h_mm=34)

    # --- Topic importance matrix (replaces noisy keyword chart) ---
    pdf.add_page()
    _heading(pdf, "AI topic importance matrix", size=12)
    _body(
        pdf,
        "Importance and depth are heuristics from topic summaries and transcript overlap; sentiment reads topic wording.",
        limit=320,
    )
    hdr = ["Topic", "Importance", "Sentiment", "Depth"]
    cw = [pdf.epw * 0.40, pdf.epw * 0.20, pdf.epw * 0.20, pdf.epw * 0.20]
    _data_table(pdf, hdr, matrix_rows, cw)

    # --- Business insights ---
    pdf.add_page()
    _heading(pdf, "Business insights", size=12)
    _subheading(pdf, "Client pain signals")
    pains = pain_points_from_polished(pt)
    if pains:
        for i, p in enumerate(pains, 1):
            _body(pdf, f"{i}. {p}", limit=500)
    else:
        _body(pdf, "No structured pain fields.")

    _subheading(pdf, "Client signals (meeting-specific)")
    sigs = tactical_client_signals(cq, pt, transcript, topics if isinstance(topics, list) else [], cov)
    if sigs:
        for s in sigs:
            _body(pdf, f"- {s}", limit=700)
    else:
        _body(pdf, "Add question_coverage + richer transcript for stronger signals.")

    _subheading(pdf, "AI observations (non-generic)")
    fins = filtered_insights(cq)
    if fins:
        for x in fins:
            _body(pdf, f"- {x}", limit=650)
    else:
        _body(pdf, "(Filtered empty — see call quality in product.)")

    _subheading(pdf, "Risks and blockers")
    if rlist:
        for r in rlist[:10]:
            _body(pdf, f"{risk_severity_prefix(r)}{r}", limit=500)
    else:
        _body(pdf, "No risk bullets.")

    # --- Confidence + gaps ---
    pdf.add_page()
    _heading(pdf, "Discovery checklist (questions, status, answers)", size=12)
    _discovery_blocks_pdf(pdf, cov)

    _heading(pdf, "What was not fully nailed", size=11)
    if pending_areas:
        _body(pdf, "Gaps to close in follow-up:\n" + "\n".join(f"- {m}" for m in pending_areas), limit=500)
    else:
        _body(pdf, "No checklist gaps flagged (or checklist not in this export).")

    # --- Action center ---
    pdf.add_page()
    _heading(pdf, "Action center", size=12)
    _subheading(pdf, "Written conclusion from analysis")
    if concl_text:
        _body(pdf, concl_text, limit=4500)
    else:
        _body(pdf, "No conclusion block on this export.", limit=120)
    _subheading(pdf, "Next steps (assign owners in your system of record)")
    if merged_steps:
        _actions_rich_table(pdf, merged_steps)
    else:
        _body(pdf, "No next_actions or polished next_steps on this export.", limit=120)

    _subheading(pdf, "Decisions / commitments")
    decs = parse_polished_list(pt.get("next_steps"))
    if decs:
        for d in decs[:12]:
            _body(pdf, f"[Commitment] {d}", limit=400)
    else:
        _body(pdf, "No parsed polished next_steps.")

    _subheading(pdf, "Timeline signal")
    tl = str(ef.get("timeline") or pt.get("timeline") or "").strip()
    _body(pdf, tl or "(Not captured.)", limit=600)

    # --- Technical ---
    pdf.add_page()
    _heading(pdf, "Technical snapshot", size=12)
    techs = list(ef.get("techstack_platform") or [])
    if isinstance(techs, list) and techs:
        _body(pdf, "Systems / platforms:\n- " + "\n- ".join(str(t) for t in techs[:22]), limit=1200)
    else:
        td = str(pt.get("technical_details") or "").strip()
        _body(pdf, td[:1400] if td else "No platform list.", limit=1600)
    _subheading(pdf, "Compliance themes (inferred)")
    cm = compliance_mentions(ef, rlist)
    _body(pdf, "\n".join(f"- {c}" for c in cm) if cm else "—", limit=400)

    # --- Strategic assessment ---
    pdf.add_page()
    _heading(pdf, "Strategic AI assessment", size=12)
    _body(
        pdf,
        "Synthesized only from structured assessment fields (no new model call). "
        "Use as internal exec read — validate commercially before client send.",
        limit=280,
    )
    for line in strategic_assessment_bullets(cq, ef, risk):
        _body(pdf, f"- {line}", limit=500)

    # --- Appendix: evidence quotes only (no raw transcript dump) ---
    pdf.add_page()
    _heading(pdf, "Key quotes (evidence)", size=11)
    hl = smart_quote_highlights(transcript, max_n=5)
    if hl:
        for quote in hl:
            _body(pdf, quote, limit=500, h=6.0)
            pdf.ln(2)
    else:
        _body(pdf, "No high-signal quotes auto-selected.", limit=200)
    _body(
        pdf,
        "The full call transcript is intentionally omitted from this PDF. Export the meeting JSON from the product when you need every line.",
        limit=320,
    )

    out = pdf.output()
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)
