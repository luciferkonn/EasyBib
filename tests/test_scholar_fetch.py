import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("skills/easybib/scripts/scholar_fetch.py").resolve()
FIXTURES = Path("tests/fixtures/scholar").resolve()


def run(extra_env, *args):
    env = {"EASYBIB_SCHOLAR_FIXTURES": str(FIXTURES)}
    env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
        env={**__import__("os").environ, **env},
    )


def test_hit_returns_bibtex_and_key():
    r = run({}, "bert")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["found"] is True
    assert data["key"].startswith("devlin2018")
    assert "BERT" in data["bibtex"]


def test_block_returns_found_false_not_crash():
    r = run({"EASYBIB_SCHOLAR_SIMULATE": "block"}, "anything")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["found"] is False
    assert "blocked" in data["reason"].lower()


def test_no_hit_returns_found_false():
    r = run({"EASYBIB_SCHOLAR_SIMULATE": "empty"}, "nothing found")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["found"] is False
