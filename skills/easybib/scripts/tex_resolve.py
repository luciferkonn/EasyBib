#!/usr/bin/env python3
"""Resolve a main .tex file and follow \\input, \\include, \\subfile.

Usage: tex_resolve.py <main.tex>
Emits JSON {"files": [...], "warnings": [...]} to stdout.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_INCLUDE = re.compile(r"\\(?:input|include|subfile)\s*\{([^}]+)\}")
_COMMENT = re.compile(r"(?<!\\)%[^\n]*")


def resolve(main: Path) -> tuple[list[str], list[str]]:
    root = main.parent.resolve()
    visited: set[Path] = set()
    order: list[Path] = []
    warnings: list[str] = []

    def _visit(path: Path) -> None:
        p = path.resolve()
        if p in visited:
            warnings.append(f"already included, skipping: {path}")
            return
        if not p.exists():
            warnings.append(f"included file not found: {path}")
            return
        visited.add(p)
        order.append(p)
        text = _COMMENT.sub("", p.read_text())
        for m in _INCLUDE.finditer(text):
            target = m.group(1).strip()
            candidates = [
                p.parent / target,
                p.parent / f"{target}.tex",
                root / target,
                root / f"{target}.tex",
            ]
            found = next((c for c in candidates if c.exists()), None)
            if found is None:
                warnings.append(f"included file not found: {target}")
                continue
            _visit(found)

    _visit(main)
    return [str(p) for p in order], warnings


def main_cli(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    main = Path(argv[1])
    if not main.exists():
        print(f"error: main tex file not found: {main}", file=sys.stderr)
        return 1
    files, warnings = resolve(main)
    json.dump({"files": files, "warnings": warnings}, sys.stdout, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main_cli(sys.argv))
