#!/usr/bin/env python3
"""Load .easybib.toml with defaults.

Usage: config.py load <project_dir>
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

try:
    import tomllib as _toml  # type: ignore[attr-defined]
except ImportError:
    import tomli as _toml  # type: ignore

DEFAULTS: dict = {
    "prefer_preprint": False,
    "main_tex": None,
    "placeholder_patterns": ["", "?", "TODO", "FIXME", "XXX"],
    "confidence_high": 0.90,
    "confidence_medium": 0.70,
    "group_by": ["section"],
}


def load(project_dir: Path) -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    path = project_dir / ".easybib.toml"
    if path.exists():
        with path.open("rb") as f:
            try:
                data = _toml.load(f)
            except _toml.TOMLDecodeError as exc:
                print(f"config: malformed .easybib.toml: {exc}", file=sys.stderr)
                sys.exit(1)
        for k, v in data.items():
            if k in DEFAULTS:
                cfg[k] = v
    return cfg


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] != "load":
        print(__doc__, file=sys.stderr)
        return 2
    cfg = load(Path(sys.argv[2]))
    json.dump(cfg, sys.stdout, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
