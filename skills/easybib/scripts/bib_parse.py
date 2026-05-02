#!/usr/bin/env python3
"""Parse and write .bib files while preserving per-entry raw text.

Usage:
    bib_parse.py parse <path>            # emits JSON list of entries on stdout
    bib_parse.py write <path> <json>     # writes entries (JSON file) to <path>
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Entry:
    key: str
    type: str
    fields: dict
    raw_text: str
    line_start: int
    line_end: int


_ENTRY_START = re.compile(r"@(?P<type>[A-Za-z]+)\s*\{\s*(?P<key>[^,\s]+)\s*,")

_SKIP_TYPES = {"string", "comment", "preamble"}


def _strip_quoted(line: str) -> str:
    """Replace characters inside double-quoted spans with spaces so that
    `{`/`}` inside string values are not counted toward brace depth.
    Handles backslash-escaped characters (e.g. `\\"`) inside quoted spans.
    """
    result = []
    in_quotes = False
    i = 0
    while i < len(line):
        ch = line[i]
        if in_quotes and ch == "\\" and i + 1 < len(line):
            result.append(" ")
            result.append(" ")
            i += 2
            continue
        if ch == '"':
            in_quotes = not in_quotes
            result.append(ch)
        elif in_quotes:
            result.append(" ")
        else:
            result.append(ch)
        i += 1
    return "".join(result)


def _brace_depth(line: str) -> int:
    """Return net brace depth change for *line*, ignoring quoted spans."""
    stripped = _strip_quoted(line)
    return stripped.count("{") - stripped.count("}")


def _consume_block(lines: list[str], start: int) -> int:
    """Walk forward from *start* until the brace block that opened on lines[start]
    is closed.  Returns the index *j* such that lines[start:j] is the full block.
    Raises ValueError on unbalanced braces.
    """
    depth = _brace_depth(lines[start])
    j = start + 1
    while j < len(lines) and depth > 0:
        depth += _brace_depth(lines[j])
        j += 1
    if depth != 0:
        raise ValueError(
            f"malformed entry starting at line {start + 1}: unbalanced braces"
        )
    return j


def parse(path: Path) -> list[Entry]:
    text = path.read_text()
    lines = text.splitlines(keepends=True)
    entries: list[Entry] = []
    i = 0
    while i < len(lines):
        m = _ENTRY_START.match(lines[i])
        if not m:
            if lines[i].lstrip().startswith("@"):
                # Check whether this is a known skip-type directive.
                type_match = re.match(r"@([A-Za-z]+)", lines[i].lstrip())
                if type_match and type_match.group(1).lower() in _SKIP_TYPES:
                    # Consume the whole directive block without recording it.
                    i = _consume_block(lines, i)
                    continue
                raise ValueError(
                    f"malformed entry at line {i + 1}: missing comma after key"
                )
            i += 1
            continue
        start_line = i + 1
        j = _consume_block(lines, i)
        raw_text = "".join(lines[i:j]).rstrip("\n")
        body = "".join(lines[i:j])[m.end():]
        fields = _parse_fields(body)
        entries.append(
            Entry(
                key=m.group("key"),
                type=m.group("type").lower(),
                fields=fields,
                raw_text=raw_text,
                line_start=start_line,
                line_end=j,
            )
        )
        i = j
    return entries


_FIELD_RE = re.compile(
    r"(?P<name>[A-Za-z][A-Za-z0-9_-]*)\s*=\s*"
    r"(?:\{(?P<braces>(?:[^{}]|\{[^{}]*\})*)\}|\"(?P<quotes>[^\"]*)\"|(?P<bare>[^,\n}]+?))"
    r"\s*(?:,|\})",
    re.DOTALL,
)


def _parse_fields(body: str) -> dict:
    fields = {}
    for m in _FIELD_RE.finditer(body):
        name = m.group("name").lower()
        value = m.group("braces") or m.group("quotes") or m.group("bare") or ""
        fields[name] = value.strip()
    return fields


def _cmd_parse(path: str) -> int:
    try:
        entries = parse(Path(path))
    except (ValueError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 2
    json.dump([asdict(e) for e in entries], sys.stdout, indent=2)
    return 0


def _cmd_write(path: str, json_path: str) -> int:
    try:
        entries = json.loads(Path(json_path).read_text())
        content = "\n\n".join(e["raw_text"] for e in entries) + "\n"
        tmp = Path(path + ".tmp")
        tmp.write_text(content)
        replaced = False
        try:
            tmp.replace(path)
            replaced = True
        finally:
            if not replaced:
                tmp.unlink(missing_ok=True)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"invalid JSON: {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(str(e), file=sys.stderr)
        return 2
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    cmd = argv[1]
    if cmd == "parse" and len(argv) == 3:
        return _cmd_parse(argv[2])
    if cmd == "write" and len(argv) == 4:
        return _cmd_write(argv[2], argv[3])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
