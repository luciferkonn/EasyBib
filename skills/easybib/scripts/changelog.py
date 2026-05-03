#!/usr/bin/env python3
"""Append a JSON record (from stdin) to a JSONL changelog file.

Usage: changelog.py append <log_path>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path


def append(log_path: Path, record: dict) -> None:
    record = dict(record)
    record.setdefault("ts", time.time())
    with log_path.open("a") as f:
        f.write(json.dumps(record) + "\n")


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] != "append":
        print(__doc__, file=sys.stderr)
        return 2
    record = json.load(sys.stdin)
    append(Path(sys.argv[2]), record)
    return 0


if __name__ == "__main__":
    sys.exit(main())
