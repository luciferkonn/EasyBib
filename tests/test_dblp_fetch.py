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


def test_corrupt_cache_is_treated_as_miss(tmp_path):
    # Pre-populate a corrupt cache file for the query
    cache_dir = tmp_path / "dblp"
    cache_dir.mkdir(parents=True)
    # use the sha1 slug that would be produced by the query
    import hashlib
    slug = hashlib.sha1(b"attention is all you need").hexdigest()[:16]
    (cache_dir / f"search_{slug}.json").write_text("this is not json")

    r = run({"EASYBIB_CACHE_DIR": str(tmp_path)},
            "search", "attention is all you need")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    # fell through to fixture; got 2 candidates
    assert len(data["candidates"]) == 2


def test_prefer_preprint_flag_works_before_query():
    r = run(None, "search", "--prefer-preprint", "attention is all you need")
    assert r.returncode == 0, r.stderr


def test_corr_is_not_confused_with_correlli(tmp_path):
    # Direct unit-ish test of _classify_type via a fixture search hit
    fx = tmp_path / "dblp"
    fx.mkdir()
    (fx / "x_search.json").write_text(json.dumps({
        "result": {"hits": {"hit": [
            {"info": {
                "key": "journals/correlli/X",
                "type": "Journal Articles",
                "title": "X",
                "authors": {"author": [{"text": "A"}]},
                "venue": "Correlli",
                "year": "2000",
            }}
        ]}}
    }))
    r = run({"EASYBIB_DBLP_FIXTURES": str(fx)}, "search", "x")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["candidates"][0]["type"] == "journals"  # not "corr"


def test_earliest_year_wins_across_types(tmp_path):
    # Construct a fixture where corr is earlier than conf and default mode still prefers year
    # default (prefer_preprint=False) should sort by year first per spec,
    # but the corr at earlier year beats conf at later year
    fx = tmp_path / "dblp"
    fx.mkdir()
    (fx / "yeartest_search.json").write_text(json.dumps({
        "result": {"hits": {"hit": [
            {"info": {
                "key": "conf/nips/X22", "type": "Conference...",
                "title": "X", "authors": {"author": [{"text": "A"}]},
                "venue": "NIPS", "year": "2022",
            }},
            {"info": {
                "key": "journals/corr/X16", "type": "Informal",
                "title": "X", "authors": {"author": [{"text": "A"}]},
                "venue": "CoRR", "year": "2016",
            }},
        ]}}
    }))
    cache_dir = tmp_path / "cache"
    r = run({"EASYBIB_DBLP_FIXTURES": str(fx), "EASYBIB_CACHE_DIR": str(cache_dir)},
            "search", "yeartest")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    # year 2016 comes before year 2022 regardless of type rank
    assert data["candidates"][0]["year"] == 2016


def test_bibtex_fixture_by_readable_name(tmp_path):
    # Use a human-readable fixture file derived from the last path component of the key.
    fx = tmp_path / "dblp"
    fx.mkdir()
    key_tail_slug = "vaswanispujgkp17"
    bibtex_data = {"bibtex": "@inproceedings{X, year=2017}\n"}
    (fx / f"bib_{key_tail_slug}.json").write_text(json.dumps(bibtex_data))
    r = run({"EASYBIB_DBLP_FIXTURES": str(fx)}, "bibtex", "conf/nips/VaswaniSPUJGKP17")
    assert r.returncode == 0, r.stderr
    assert "@inproceedings" in r.stdout
