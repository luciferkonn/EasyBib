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


def test_last_first_author_format_produces_correct_key(tmp_path):
    # Fixture has "Devlin, Jacob" — key should still start with devlin2018
    # Use tmp_path to bypass any stale default cache
    r = run({"EASYBIB_CACHE_DIR": str(tmp_path)}, "bert")
    data = json.loads(r.stdout)
    assert data["found"] is True
    assert data["key"].startswith("devlin2018"), f"expected key starting devlin2018, got {data['key']}"


def test_cache_hit_on_second_call(tmp_path):
    # First call populates cache; second call reads from cache
    r1 = run({"EASYBIB_CACHE_DIR": str(tmp_path)}, "bert")
    assert r1.returncode == 0, r1.stderr
    data1 = json.loads(r1.stdout)
    assert data1["found"] is True
    # Locate the cache file and overwrite with a marker
    import hashlib
    slug = hashlib.sha1(b"bert").hexdigest()[:16]
    cache_file = tmp_path / "scholar" / f"{slug}.json"
    assert cache_file.exists()
    cache_file.write_text(json.dumps({"found": True, "key": "cached_marker", "bibtex": "@cached{}"}))
    r2 = run({"EASYBIB_CACHE_DIR": str(tmp_path)}, "bert")
    assert r2.returncode == 0
    data2 = json.loads(r2.stdout)
    assert data2["key"] == "cached_marker"


def test_corrupt_cache_is_treated_as_miss(tmp_path):
    import hashlib
    slug = hashlib.sha1(b"bert").hexdigest()[:16]
    cache_dir = tmp_path / "scholar"
    cache_dir.mkdir(parents=True)
    (cache_dir / f"{slug}.json").write_text("not json")
    r = run({"EASYBIB_CACHE_DIR": str(tmp_path)}, "bert")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["found"] is True  # fixture path resolved
