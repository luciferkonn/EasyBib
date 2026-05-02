#!/usr/bin/env python3
"""Score a bibtex entry against DBLP/Scholar candidates using rapidfuzz.

Reads JSON on stdin:
    {"entry": {"title": str, "authors": [str, ...]},
     "candidates": [{"id": str, "title": str, "authors": [str, ...]}, ...],
     "thresholds": {"high": 0.90, "medium": 0.70}}  # thresholds optional

Writes JSON on stdout:
    {"tier": "high"|"medium"|"low"|"none",
     "scored": [{"id": str, "score": float}, ...]}
"""
from __future__ import annotations

import json
import sys

from rapidfuzz import fuzz

DEFAULT_HIGH = 0.90
DEFAULT_MEDIUM = 0.70


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def _title_score(a: str, b: str) -> float:
    return fuzz.token_set_ratio(_norm(a), _norm(b)) / 100.0


def _author_overlap(a: list[str], b: list[str]) -> float:
    if not a or not b:
        return 0.0
    la = {_norm(x).split()[-1] for x in a if x.strip()}
    lb = {_norm(x).split()[-1] for x in b if x.strip()}
    if not la or not lb:
        return 0.0
    return len(la & lb) / len(la | lb)


def score(entry: dict, candidate: dict) -> float:
    t = _title_score(entry.get("title", ""), candidate.get("title", ""))
    a = _author_overlap(entry.get("authors", []), candidate.get("authors", []))
    return 0.8 * t + 0.2 * a


def tier_for(score_: float, high: float, medium: float) -> str:
    if score_ >= high:
        return "high"
    if score_ >= medium:
        return "medium"
    if score_ > 0:
        return "low"
    return "none"


def main() -> int:
    payload = json.load(sys.stdin)
    entry = payload["entry"]
    candidates = payload["candidates"]
    thresholds = payload.get("thresholds", {})
    high = float(thresholds.get("high", DEFAULT_HIGH))
    medium = float(thresholds.get("medium", DEFAULT_MEDIUM))
    scored = sorted(
        ({"id": c["id"], "score": score(entry, c)} for c in candidates),
        key=lambda x: x["score"],
        reverse=True,
    )
    top = scored[0]["score"] if scored else 0.0
    tier = tier_for(top, high, medium) if scored else "none"
    json.dump({"tier": tier, "scored": scored}, sys.stdout, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
