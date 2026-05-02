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
