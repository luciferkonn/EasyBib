#!/usr/bin/env python3
"""Search DBLP and fetch condensed bibtex, with file-based caching.

Usage:
    dblp_fetch.py search <query> [--prefer-preprint]
    dblp_fetch.py bibtex <dblp_key>

Environment:
    EASYBIB_CACHE_DIR       — cache dir (default .easybib-cache).
    EASYBIB_DBLP_FIXTURES   — if set, load <slug>.json from this dir in place of HTTP.
    EASYBIB_OFFLINE         — if set, error on any non-cached, non-fixture access.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

DBLP_SEARCH = "https://dblp.org/search/publ/api"
DBLP_BIB = "https://dblp.org/rec/{key}.bib"
CACHE_TTL = 7 * 24 * 3600


def _cache_dir() -> Path:
    d = Path(os.environ.get("EASYBIB_CACHE_DIR", ".easybib-cache")) / "dblp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_get(slug: str) -> dict | None:
    p = _cache_dir() / f"{slug}.json"
    if not p.exists():
        return None
    if time.time() - p.stat().st_mtime > CACHE_TTL:
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _cache_put(slug: str, obj: dict) -> None:
    p = _cache_dir() / f"{slug}.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj))
    tmp.replace(p)


def _slug(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:16]


def _fixture(slug_name: str) -> dict | None:
    fx = os.environ.get("EASYBIB_DBLP_FIXTURES")
    if not fx:
        return None
    p = Path(fx) / f"{slug_name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _fetch_search(query: str) -> dict:
    cached = _cache_get(f"search_{_slug(query)}")
    if cached is not None:
        return cached
    fixture_name = re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_").split("_")[0]
    fx = _fixture(f"{fixture_name}_search")
    if fx is not None:
        _cache_put(f"search_{_slug(query)}", fx)
        return fx
    if os.environ.get("EASYBIB_OFFLINE"):
        raise RuntimeError(f"offline and no cache for: {query}")
    for attempt in range(3):
        try:
            r = requests.get(
                DBLP_SEARCH,
                params={"q": query, "format": "json", "h": 30},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            _cache_put(f"search_{_slug(query)}", data)
            return data
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status and status < 500:
                raise  # don't retry 4xx
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def _classify_type(dblp_key: str) -> str:
    if dblp_key.startswith("conf/"):
        return "conf"
    if dblp_key.startswith("journals/corr/"):
        return "corr"
    if dblp_key.startswith("journals/"):
        return "journals"
    return "other"


def _sort_candidates(cands: list[dict], prefer_preprint: bool) -> list[dict]:
    def key(c):
        t = c["type"]
        corr_rank = 0 if prefer_preprint else 2
        type_rank = {"conf": 0, "journals": 1, "corr": corr_rank, "other": 3}.get(t, 3)
        return (c["year"], type_rank, c["dblp_key"])

    return sorted(cands, key=key)


def search(query: str, prefer_preprint: bool = False) -> list[dict]:
    data = _fetch_search(query)
    hits = data.get("result", {}).get("hits", {}).get("hit", []) or []
    candidates: list[dict] = []
    for h in hits:
        info = h.get("info", {})
        authors_field = info.get("authors", {}) or {}
        author_list = authors_field.get("author", []) or []
        if isinstance(author_list, dict):
            author_list = [author_list]
        authors = [a.get("text", "") for a in author_list]
        candidates.append(
            {
                "dblp_key": info.get("key", ""),
                "title": info.get("title", ""),
                "authors": authors,
                "year": int(info.get("year", 0)) if str(info.get("year", "")).isdigit() else 0,
                "venue": info.get("venue", ""),
                "type": _classify_type(info.get("key", "")),
                "doi": info.get("doi"),
            }
        )
    return _sort_candidates(candidates, prefer_preprint)


def _bibtex_fixture_slug(dblp_key: str) -> str:
    tail = dblp_key.rsplit("/", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "_", tail.lower()).strip("_")


def fetch_bibtex(dblp_key: str) -> str:
    cached_key = f"bib_{_slug(dblp_key)}"
    cached = _cache_get(cached_key)
    if cached is not None:
        return cached["bibtex"]
    fx_slug = _bibtex_fixture_slug(dblp_key)
    fx = _fixture(f"bib_{fx_slug}")
    if fx is not None:
        return fx["bibtex"]
    if os.environ.get("EASYBIB_OFFLINE"):
        raise RuntimeError(f"offline and no cache for key: {dblp_key}")
    for attempt in range(3):
        try:
            r = requests.get(DBLP_BIB.format(key=dblp_key), params={"param": 0}, timeout=10)
            r.raise_for_status()
            text = r.text
            _cache_put(cached_key, {"bibtex": text})
            return text
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status and status < 500:
                raise  # don't retry 4xx
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def _cmd_search(args: list[str]) -> int:
    prefer = False
    positional: list[str] = []
    for a in args:
        if a == "--prefer-preprint":
            prefer = True
        else:
            positional.append(a)
    if not positional:
        print(__doc__, file=sys.stderr)
        return 2
    query = positional[0]
    try:
        cands = search(query, prefer_preprint=prefer)
    except (requests.RequestException, RuntimeError, json.JSONDecodeError) as e:
        print(str(e), file=sys.stderr)
        return 3
    json.dump({"candidates": cands}, sys.stdout, indent=2)
    return 0


def main_cli(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    cmd = argv[1]
    if cmd == "search":
        return _cmd_search(argv[2:])
    if cmd == "bibtex":
        if len(argv) < 3:
            return 2
        try:
            text = fetch_bibtex(argv[2])
        except (requests.RequestException, RuntimeError) as e:
            print(str(e), file=sys.stderr)
            return 3
        sys.stdout.write(text)
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main_cli(sys.argv))
