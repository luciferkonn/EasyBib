import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("skills/easybib/scripts/dblp_fetch.py").resolve()
FIXTURES = Path("tests/fixtures/dblp").resolve()


def run(env=None, *args):
    e = {"EASYBIB_DBLP_FIXTURES": str(FIXTURES), "PATH": "/usr/bin:/bin"}
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, env={**__import__("os").environ, **e},
    )


def test_search_returns_candidates_sorted_default_prefers_peer_reviewed():
    r = run(None, "search", "attention is all you need")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    cands = data["candidates"]
    assert len(cands) == 2
    assert cands[0]["dblp_key"].startswith("conf/")
    assert cands[0]["type"] == "conf"
    assert cands[0]["year"] == 2017


def test_search_with_prefer_preprint_puts_corr_first_only_if_earlier():
    r = run(None, "search", "attention is all you need", "--prefer-preprint")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    cands = data["candidates"]
    assert cands[0]["year"] <= cands[-1]["year"]


def test_search_zero_hits_returns_empty_list():
    r = run(None, "search", "bert")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["candidates"] == []


def test_cache_is_used_on_second_call(tmp_path):
    r1 = run({"EASYBIB_CACHE_DIR": str(tmp_path)}, "search", "attention is all you need")
    assert r1.returncode == 0
    r2 = run({"EASYBIB_CACHE_DIR": str(tmp_path), "EASYBIB_OFFLINE": "1"},
             "search", "attention is all you need")
    assert r2.returncode == 0, r2.stderr
    data = json.loads(r2.stdout)
    assert data["candidates"][0]["dblp_key"].startswith("conf/")
