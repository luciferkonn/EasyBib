#!/usr/bin/env python3
"""Reorder .bib entries by first-appearance section.

Reads JSON on stdin:
    {
      "entries":    [{"key": ..., "raw_text": ...}, ...],
      "cite_order": [{"key": ..., "section": ...}, ...]   # document order
    }

Writes the reorganized .bib text on stdout.
"""
from __future__ import annotations

import json
import sys

PREAMBLE = "__preamble__"


def organize(entries: list[dict], cite_order: list[dict]) -> str:
    first_section: dict[str, str] = {}
    section_order: list[str] = []
    for c in cite_order:
        k = c["key"]
        sec = c.get("section") or PREAMBLE
        if k in first_section:
            continue
        first_section[k] = sec
        if sec not in section_order:
            section_order.append(sec)

    by_section: dict[str, list[dict]] = {s: [] for s in section_order}
    unused: list[dict] = []
    placed: set[str] = set()
    entry_by_key = {e["key"]: e for e in entries}

    for c in cite_order:
        k = c["key"]
        if k in placed:
            continue
        target = entry_by_key.get(k)
        if target is None:
            continue
        sec = first_section[k]
        by_section[sec].append(target)
        placed.add(k)

    for e in entries:
        if e["key"] not in placed:
            unused.append(e)

    def header(sec: str) -> str:
        if sec == PREAMBLE:
            return "% === Preamble ==="
        return f"% === {sec} ==="

    parts: list[str] = []
    for sec in section_order:
        if not by_section[sec]:
            continue
        parts.append(header(sec))
        parts.extend(e["raw_text"] for e in by_section[sec])
    if unused:
        parts.append("% === Unused ===")
        parts.extend(e["raw_text"] for e in unused)
    return "\n\n".join(parts) + "\n"


def main() -> int:
    payload = json.load(sys.stdin)
    sys.stdout.write(organize(payload["entries"], payload["cite_order"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
