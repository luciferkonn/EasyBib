import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(".").resolve()
BIB_PARSE = ROOT / "skills/easybib/scripts/bib_parse.py"
DBLP_FETCH = ROOT / "skills/easybib/scripts/dblp_fetch.py"
FUZZY = ROOT / "skills/easybib/scripts/fuzzy_match.py"
PROJ_FIXTURE = ROOT / "tests/fixtures/projects/check_basic"
DBLP_FIXTURES = ROOT / "tests/fixtures/dblp"


def run(cmd, input_=None, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(cmd, input=input_, capture_output=True, text=True, env=e)


def test_check_flags_known_high_and_unknown_none(tmp_path):
    work = tmp_path / "proj"
    shutil.copytree(PROJ_FIXTURE, work)
    env = {"EASYBIB_DBLP_FIXTURES": str(DBLP_FIXTURES),
           "EASYBIB_CACHE_DIR": str(tmp_path / "cache")}

    parse = run([sys.executable, str(BIB_PARSE), "parse", str(work / "refs.bib")])
    entries = json.loads(parse.stdout)

    tiers = {}
    for entry in entries:
        search = run(
            [sys.executable, str(DBLP_FETCH), "search",
             f"{entry['fields'].get('title', '')} {entry['fields'].get('author', '')}"],
            env=env,
        )
        assert search.returncode == 0, search.stderr
        cands = json.loads(search.stdout)["candidates"]
        fuzzy_in = {
            "entry": {"title": entry["fields"].get("title", ""),
                      "authors": [entry["fields"].get("author", "")]},
            "candidates": [
                {"id": c["dblp_key"], "title": c["title"], "authors": c["authors"]}
                for c in cands
            ],
        }
        fuzzy = run([sys.executable, str(FUZZY)], input_=json.dumps(fuzzy_in))
        tiers[entry["key"]] = json.loads(fuzzy.stdout)["tier"]

    assert tiers["vaswani17"] == "high"
    assert tiers["totally_unknown"] == "none"
