"""Pure helpers for insight charts (no Streamlit)."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

import pandas as pd


def parse_ts(ts: str) -> float:
    try:
        parts = str(ts).strip().split(":")
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
            return h * 3600 + m * 60 + s
        if len(parts) == 2:
            m, s = int(parts[0]), float(parts[1])
            return m * 60 + s
    except (ValueError, TypeError):
        pass
    return 0.0


def segment_density(transcript: list[dict[str, Any]], bin_sec: int = 60) -> pd.DataFrame:
    if not transcript:
        return pd.DataFrame({"minute": [], "segments": []})
    max_end = max(parse_ts(s.get("end", "0")) for s in transcript)
    n_bins = max(1, int(max_end // bin_sec) + 1)
    counts = [0] * n_bins
    for s in transcript:
        start = parse_ts(s.get("start", "0"))
        end = parse_ts(s.get("end", str(start)))
        mid = (start + end) / 2.0
        b = min(int(mid // bin_sec), n_bins - 1)
        counts[b] += 1
    minutes = [(i * bin_sec) / 60.0 for i in range(n_bins)]
    return pd.DataFrame({"minute": minutes, "segments": counts})


def speaker_share(transcript: list[dict[str, Any]], top: int = 8) -> pd.Series:
    labels = []
    for s in transcript:
        r = s.get("role") or s.get("speaker") or "Unknown"
        labels.append(str(r))
    ser = pd.Series(labels).value_counts()
    if len(ser) > top:
        other = ser.iloc[top:].sum()
        ser = ser.iloc[:top]
        if other > 0:
            ser["Other"] = int(other)
    total = ser.sum()
    if total <= 0:
        return ser
    return (ser / total * 100.0).round(1)


_POS = frozenset(
    "great good excellent yes interested love excited happy valuable strong clear win success progress agree opportunity".split()
)
_NEG = frozenset(
    "bad concern risk worried delay problem difficult expensive issue uncertain hesitate budget tight challenge wrong".split()
)


def sentiment_curve(transcript: list[dict[str, Any]], n_bins: int = 14) -> pd.DataFrame:
    if not transcript:
        return pd.DataFrame({"minute": [], "tone": []})
    max_end = max(parse_ts(s.get("end", "0")) for s in transcript) or 1.0
    texts: list[list[str]] = [[] for _ in range(n_bins)]
    for s in transcript:
        mid = (parse_ts(s.get("start", "0")) + parse_ts(s.get("end", "0"))) / 2.0
        b = min(int(mid / max_end * n_bins), n_bins - 1)
        words = re.findall(r"[a-zA-Z]+", str(s.get("text", "")).lower())
        texts[b].extend(words)
    scores = []
    for words in texts:
        if not words:
            scores.append(0.0)
            continue
        p = sum(1 for w in words if w in _POS)
        n = sum(1 for w in words if w in _NEG)
        denom = max(len(words), 1)
        scores.append((p - n) / denom * 3.0)
    minutes = [max_end * (i + 0.5) / n_bins / 60.0 for i in range(n_bins)]
    s = pd.Series(scores)
    if len(s) > 3:
        s = s.rolling(3, center=True, min_periods=1).mean()
    return pd.DataFrame({"minute": minutes, "tone": s.values})


_STOP = frozenset(
    "the a an and or to of is it in for on at that this with as be are was were been being from by i you we they he she them our your their not but if so than then about into out up down all any some can could would should will just only also what when where which who how more most much very into".split()
)


def top_keywords(transcript: list[dict[str, Any]], k: int = 12) -> pd.Series:
    words: list[str] = []
    for s in transcript:
        for w in re.findall(r"[a-zA-Z]{4,}", str(s.get("text", "")).lower()):
            if w not in _STOP:
                words.append(w)
    c = Counter(words)
    ser = pd.Series(dict(c.most_common(k)))
    return ser


def distinct_speakers(transcript: list[dict[str, Any]]) -> int:
    """Count unique conversation parties (prefers role, falls back to speaker label)."""
    labels: set[str] = set()
    for s in transcript:
        r = s.get("role") or s.get("speaker")
        if r:
            labels.add(str(r).strip())
    return len(labels)
