#!/usr/bin/env python3
"""Best-effort Google Scholar lookup. Returns found=False on any failure.

Usage: scholar_fetch.py <query>

Environment:
    EASYBIB_SCHOLAR_FIXTURES   — if set, load <slug>_hit.json from this dir.
    EASYBIB_SCHOLAR_SIMULATE   — "block"|"empty" for deterministic tests.
    EASYBIB_CACHE_DIR          — cache dir (default .easybib-cache).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

CACHE_TTL = 7 * 24 * 3600

JOURNAL_KEYWORDS = ("journal", "transactions", "letters", "review", "science", "nature")


def _slug(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:16]


def _cache_dir() -> Path:
    d = Path(os.environ.get("EASYBIB_CACHE_DIR", ".easybib-cache")) / "scholar"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_cache(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(obj))
        tmp.replace(path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def _fixture(query: str) -> dict | None:
    fx = os.environ.get("EASYBIB_SCHOLAR_FIXTURES")
    if not fx:
        return None
    fixture_name = re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_").split("_")[0]
    p = Path(fx) / f"{fixture_name}_hit.json"
    return json.loads(p.read_text()) if p.exists() else None


def _last_name(author: str) -> str:
    """Return the last name from 'First Last' or 'Last, First' formats, lowercased."""
    normed = author.strip()
    if not normed:
        return ""
    if "," in normed:
        return normed.split(",", 1)[0].strip().split()[-1].lower()
    tokens = normed.split()
    return tokens[-1].lower() if tokens else ""


def _make_key(first_author: str, year: str, title: str) -> str:
    last = _last_name(first_author) or "anon"
    first_word = next(
        (w for w in re.findall(r"[A-Za-z]+", title) if len(w) > 3), "paper"
    ).lower()
    return f"{last}{year}{first_word}"


def _is_journal_venue(venue: str) -> bool:
    v = venue.lower()
    return any(kw in v for kw in JOURNAL_KEYWORDS)


def _compose_bibtex(hit: dict, key: str) -> str:
    venue = hit.get("venue", "")
    is_article = _is_journal_venue(venue)
    kind = "@article" if is_article else "@inproceedings"
    venue_field = "journal" if is_article else "booktitle"
    authors = " and ".join(hit.get("authors", []))
    return (
        f"{kind}{{{key},\n"
        f"  author = {{{authors}}},\n"
        f"  title  = {{{hit.get('title', '')}}},\n"
        f"  {venue_field} = {{{venue}}},\n"
        f"  year   = {{{hit.get('year', '')}}},\n"
        f"}}\n"
    )


def lookup(query: str) -> dict:
    sim = os.environ.get("EASYBIB_SCHOLAR_SIMULATE")
    if sim == "block":
        return {"found": False, "reason": "scholar_blocked"}
    if sim == "empty":
        return {"found": False, "reason": "no_hits"}
    cache_file = _cache_dir() / f"{_slug(query)}.json"
    if cache_file.exists() and time.time() - cache_file.stat().st_mtime <= CACHE_TTL:
        try:
            return json.loads(cache_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    fx = _fixture(query)
    if fx is not None:
        key = _make_key(fx.get("authors", [""])[0] if fx.get("authors") else "",
                        str(fx.get("year", "")), fx.get("title", ""))
        result = {"found": True, "key": key, "bibtex": _compose_bibtex(fx, key)}
        _write_cache(cache_file, result)
        return result
    try:
        from scholarly import scholarly  # type: ignore
        hits = scholarly.search_pubs(query)
        first = next(hits, None)
        if first is None:
            result = {"found": False, "reason": "no_hits"}
            _write_cache(cache_file, result)
            return result
        bib = first.get("bib", {})
        hit = {
            "title": bib.get("title", ""),
            "authors": (
                bib.get("author", "").split(" and ")
                if isinstance(bib.get("author"), str)
                else bib.get("author", [])
            ),
            "year": str(bib.get("pub_year", "")),
            "venue": bib.get("venue", ""),
        }
        key = _make_key(hit["authors"][0] if hit["authors"] else "",
                        hit["year"], hit["title"])
        result = {"found": True, "key": key, "bibtex": _compose_bibtex(hit, key)}
        _write_cache(cache_file, result)
        return result
    except Exception as e:
        result = {"found": False, "reason": f"scholar_error: {type(e).__name__}"}
        _write_cache(cache_file, result)
        return result


def main_cli(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    result = lookup(" ".join(argv[1:]))
    json.dump(result, sys.stdout, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main_cli(sys.argv))
