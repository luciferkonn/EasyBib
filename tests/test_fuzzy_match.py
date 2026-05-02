import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("skills/easybib/scripts/fuzzy_match.py").resolve()


def run(payload):
    r = subprocess.run(
        [sys.executable, str(SCRIPT)], input=json.dumps(payload),
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_identical_title_is_high_tier():
    data = run({
        "entry": {"title": "Attention is All you Need", "authors": ["Vaswani"]},
        "candidates": [
            {"id": "c1", "title": "Attention is All you Need", "authors": ["Vaswani"]},
            {"id": "c2", "title": "Transformers Explained", "authors": ["Smith"]},
        ],
    })
    assert data["tier"] == "high"
    assert data["scored"][0]["id"] == "c1"
    assert data["scored"][0]["score"] >= 0.90


def test_minor_typo_is_still_high():
    data = run({
        "entry": {"title": "Attention is All you Need", "authors": ["Vaswani"]},
        "candidates": [
            {"id": "c1", "title": "Attention is All You Need.", "authors": ["Vaswani", "Shazeer"]},
        ],
    })
    assert data["tier"] in {"high", "medium"}


def test_wrong_paper_is_none_or_low():
    data = run({
        "entry": {"title": "Attention is All you Need", "authors": ["Vaswani"]},
        "candidates": [
            {"id": "c1", "title": "Deep Residual Learning", "authors": ["He"]},
        ],
    })
    assert data["tier"] in {"none", "low"}


def test_no_candidates_returns_none_tier():
    data = run({"entry": {"title": "X", "authors": []}, "candidates": []})
    assert data["tier"] == "none"
    assert data["scored"] == []


def test_bibtex_last_first_author_matches_dblp_first_last():
    """BibTeX entries use 'Vaswani, Ashish'; DBLP uses 'Ashish Vaswani'.
    Both must score as the same author."""
    data = run({
        "entry": {
            "title": "Attention is All you Need",
            "authors": ["Vaswani, Ashish", "Shazeer, Noam"],
        },
        "candidates": [
            {
                "id": "c1",
                "title": "Attention is All you Need",
                "authors": ["Ashish Vaswani", "Noam Shazeer"],
            },
        ],
    })
    assert data["tier"] == "high"
    assert data["scored"][0]["score"] >= 0.95


def test_malformed_stdin_exits_cleanly():
    r = subprocess.run(
        [sys.executable, str(SCRIPT)], input="not json",
        capture_output=True, text=True,
    )
    assert r.returncode == 2
    assert "Traceback" not in r.stderr


def test_missing_entry_key_exits_cleanly():
    r = subprocess.run(
        [sys.executable, str(SCRIPT)], input='{"candidates": []}',
        capture_output=True, text=True,
    )
    assert r.returncode == 2
    assert "Traceback" not in r.stderr


def test_inverted_thresholds_rejected():
    r = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({
            "entry": {"title": "X", "authors": []},
            "candidates": [],
            "thresholds": {"high": 0.5, "medium": 0.9},
        }),
        capture_output=True, text=True,
    )
    assert r.returncode == 2
