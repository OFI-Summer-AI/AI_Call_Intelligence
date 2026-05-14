"""Matplotlib figures as PNG bytes for PDF embedding (premium, no Streamlit)."""

from __future__ import annotations

import io
from collections import Counter
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from app.frontend.chart_helpers import parse_ts, sentiment_curve
from app.frontend.report_pdf_intel import momentum_phases


def _fig_to_png(fig: plt.Figure, *, dpi: int = 120) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _speaker_bins(transcript: list[dict[str, Any]], n_bins: int = 42) -> tuple[np.ndarray, list[str], float]:
    if not transcript:
        return np.zeros((1, n_bins)), ["n/a"], 1.0
    max_end = max(parse_ts(s.get("end", "0")) for s in transcript) or 1.0
    counts = Counter(str(s.get("role") or s.get("speaker") or "Unknown") for s in transcript)
    top = [k for k, _ in counts.most_common(7)]
    merge_other = len(counts) > len(top)
    labels = top + (["Other"] if merge_other else [])
    n_sp = len(labels)
    idx: dict[str, int] = {sp: i for i, sp in enumerate(top)}
    mat = np.zeros((n_sp, n_bins))
    edges = np.linspace(0.0, max_end, n_bins + 1)
    for seg in transcript:
        sp = str(seg.get("role") or seg.get("speaker") or "Unknown")
        if sp in idx:
            si = idx[sp]
        elif merge_other:
            si = len(top)
        else:
            si = idx.get(sp, 0)
        st = parse_ts(seg.get("start", "0"))
        en = parse_ts(seg.get("end", str(st)))
        for j in range(n_bins):
            b0, b1 = float(edges[j]), float(edges[j + 1])
            ov = max(0.0, min(en, b1) - max(st, b0))
            if ov > 0:
                mat[si, j] += ov
    row_max = mat.max(axis=1, keepdims=True) + 1e-6
    mat = mat / row_max
    return mat, labels, max_end


def fig_speaker_activity_heatmap(transcript: list[dict[str, Any]]) -> bytes:
    mat, labels, max_end = _speaker_bins(transcript, n_bins=44)
    fig_h = min(2.9, max(2.2, 0.26 * len(labels) + 1.35))
    fig, ax = plt.subplots(figsize=(6.1, fig_h), facecolor="#ffffff")
    ax.set_facecolor("#f8fafc")
    if mat.size == 0 or max_end < 1:
        ax.text(0.5, 0.5, "No timing data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
    else:
        im = ax.imshow(
            mat,
            aspect="auto",
            cmap="YlOrRd",
            interpolation="nearest",
            extent=[0, max_end / 60.0, len(labels) - 0.5, -0.5],
        )
        im.set_clim(0, 1)
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel("Minutes", fontsize=8, color="#334155")
        ax.set_title("Speaker activity (darker = more talk time)", fontsize=10, fontweight="600", pad=5, color="#0f172a")
    ax.spines["top"].set_visible(False)
    fig.tight_layout()
    return _fig_to_png(fig)


def fig_momentum_bars(transcript: list[dict[str, Any]]) -> bytes:
    phases = momentum_phases(transcript, n_phases=5)
    labels = [f"{a}\n{b}" for a, b, _ in phases]
    vals = [c for _, _, c in phases]
    colors = plt.cm.RdYlGn(np.linspace(0.25, 0.85, len(vals)))
    fig, ax = plt.subplots(figsize=(6.1, 2.05), facecolor="#ffffff")
    ax.set_facecolor("#f8fafc")
    y = np.arange(len(vals))
    ax.barh(y, vals, color=colors, height=0.62, edgecolor="white", linewidth=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Engagement index (normalized)", fontsize=9, color="#334155")
    ax.set_title("Meeting momentum by segment", fontsize=10, fontweight="600", pad=5, color="#0f172a")
    ax.grid(axis="x", alpha=0.25, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_png(fig)


def fig_topic_depth_bars(topic_wise: list[Any]) -> bytes:
    fig, ax = plt.subplots(figsize=(6.1, min(2.35, 0.2 * min(len(topic_wise or []), 8) + 0.95)), facecolor="#ffffff")
    ax.set_facecolor("#f8fafc")
    if not isinstance(topic_wise, list) or not topic_wise:
        ax.text(0.5, 0.5, "Topic depth chart (after topic extraction)", ha="center", va="center", fontsize=10, color="#64748b")
        ax.set_axis_off()
    else:
        rows = topic_wise[:8]
        labels: list[str] = []
        weights: list[float] = []
        for i, row in enumerate(rows):
            if isinstance(row, dict):
                t = str(row.get("topic", f"Topic {i + 1}"))[:46]
                s = str(row.get("summary", ""))
            else:
                t, s = f"Topic {i + 1}", ""
            labels.append(t)
            weights.append(float(len(s)) + len(t) * 1.5)
        mx = max(weights) or 1.0
        w_norm = [0.15 + 0.85 * (w / mx) for w in weights]
        y = np.arange(len(labels))
        cmap = plt.cm.viridis(np.linspace(0.25, 0.9, len(y)))
        ax.barh(y, w_norm, color=cmap, height=0.55, edgecolor="white", linewidth=1.0)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xticks([])
        ax.invert_yaxis()
        ax.set_title("Topic discussion depth (relative)", fontsize=10, fontweight="600", pad=5, color="#0f172a")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
    fig.tight_layout()
    return _fig_to_png(fig)


def fig_sentiment(transcript: list[dict[str, Any]]) -> bytes:
    curve = sentiment_curve(transcript, n_bins=18)
    fig, ax = plt.subplots(figsize=(6.1, 2.1), facecolor="#ffffff")
    ax.set_facecolor("#f8fafc")
    if curve.empty:
        ax.text(0.5, 0.5, "No transcript", ha="center", va="center", fontsize=10, color="#64748b")
        ax.set_axis_off()
    else:
        y = curve["tone"].values
        x = curve["minute"].values
        ax.fill_between(x, y, 0, where=(y >= 0), alpha=0.38, color="#16a34a", interpolate=True)
        ax.fill_between(x, y, 0, where=(y < 0), alpha=0.38, color="#ea580c", interpolate=True)
        ax.plot(x, y, color="#0f172a", linewidth=2.0, alpha=0.88)
        ax.axhline(0, color="#94a3b8", linewidth=0.8)
        ax.set_xlabel("Minutes", fontsize=9, color="#334155")
        ax.set_ylabel("Tone (keyword proxy)", fontsize=9, color="#334155")
    ax.set_title("Sentiment trend", fontsize=10, fontweight="600", pad=5, color="#0f172a")
    ax.grid(True, alpha=0.2, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_png(fig)


def build_intelligence_pngs(data: dict[str, Any]) -> dict[str, bytes]:
    tr = data.get("transcript") or []
    topics = data.get("topic_wise_summary") or []
    return {
        "speaker_timeline": fig_speaker_activity_heatmap(tr),
        "sentiment": fig_sentiment(tr),
        "momentum": fig_momentum_bars(tr),
        "topic_depth": fig_topic_depth_bars(topics if isinstance(topics, list) else []),
    }
