#!/usr/bin/env python3
"""Scan resolved .tex files for empty cites, cite keys, and sections.

Usage: tex_scan.py <main.tex> [--placeholders "" "?" TODO FIXME XXX]
Emits JSON {"empty_cites": [...], "cite_keys": [...], "sections": [...]}.

Invokes tex_resolve.py internally to expand includes.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

_COMMENT = re.compile(r"(?<!\\)%[^\n]*")
_SECTION = re.compile(r"\\section\*?(?:\[[^\]]*\])?\s*\{([^}]*)\}")
_CITE = re.compile(r"\\(cite|citep|citet)\s*(?:\[[^\]]*\]){0,2}\s*\{([^}]*)\}")
DEFAULT_PLACEHOLDERS = {"", "?", "TODO", "FIXME", "XXX"}
PREAMBLE = "__preamble__"
CONTEXT_CHARS = 80


def _resolve_main(main: Path) -> list[Path]:
    resolver = Path(__file__).with_name("tex_resolve.py")
    r = subprocess.run(
        [sys.executable, str(resolver), str(main)], capture_output=True, text=True, check=True
    )
    data = json.loads(r.stdout)
    return [Path(p) for p in data["files"]]


def scan(main: Path, placeholders: set[str]) -> dict:
    files = _resolve_main(main)
    empty_cites: list[dict] = []
    cite_keys: list[dict] = []
    sections: list[dict] = []
    seen_keys: set[str] = set()
    for path in files:
        text = path.read_text()
        current_section = PREAMBLE
        for line_num, line in enumerate(text.splitlines(), start=1):
            stripped_line = _COMMENT.sub(lambda m: " " * len(m.group(0)), line)
            sm = _SECTION.search(stripped_line)
            if sm:
                current_section = sm.group(1).strip()
                sections.append({"title": current_section, "file": str(path), "line": line_num})
            for m in _CITE.finditer(stripped_line):
                command = m.group(1)
                raw_keys = m.group(2).strip()
                col = m.start() + 1
                context_before = line[max(0, m.start() - CONTEXT_CHARS) : m.start()].strip()
                context_after = line[m.end() : m.end() + CONTEXT_CHARS].strip()
                if raw_keys in placeholders or all(
                    k.strip() in placeholders for k in raw_keys.split(",")
                ):
                    empty_cites.append(
                        {
                            "file": str(path),
                            "line": line_num,
                            "col": col,
                            "command": command,
                            "placeholder": raw_keys,
                            "context_before": context_before,
                            "context_after": context_after,
                        }
                    )
                    continue
                real_keys = (
                    x.strip()
                    for x in raw_keys.split(",")
                    if x.strip() and x.strip() not in placeholders
                )
                for k in real_keys:
                    cite_keys.append(
                        {
                            "key": k,
                            "file": str(path),
                            "line": line_num,
                            "section": current_section,
                            "first": k not in seen_keys,
                        }
                    )
                    seen_keys.add(k)
    return {"empty_cites": empty_cites, "cite_keys": cite_keys, "sections": sections}


def main_cli(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    main = Path(argv[1])
    placeholders = set(argv[2:]) if len(argv) > 2 else DEFAULT_PLACEHOLDERS
    try:
        result = scan(main, placeholders)
    except subprocess.CalledProcessError as e:
        if e.stderr:
            print(e.stderr.strip(), file=sys.stderr)
        return 1
    json.dump(result, sys.stdout, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main_cli(sys.argv))
