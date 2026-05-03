import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(".").resolve()
TEX_SCAN = ROOT / "skills/easybib/scripts/tex_scan.py"
BIB_PARSE = ROOT / "skills/easybib/scripts/bib_parse.py"
ORGANIZE = ROOT / "skills/easybib/scripts/organize_bib.py"
FIXTURE = ROOT / "tests/fixtures/projects/organize_basic"


def test_organize_e2e(tmp_path):
    work = tmp_path / "proj"
    shutil.copytree(FIXTURE, work)
    tex = work / "main.tex"
    bib = work / "refs.bib"

    scan = subprocess.run(
        [sys.executable, str(TEX_SCAN), str(tex)],
        capture_output=True, text=True, check=True,
    )
    scan_data = json.loads(scan.stdout)

    parse = subprocess.run(
        [sys.executable, str(BIB_PARSE), "parse", str(bib)],
        capture_output=True, text=True, check=True,
    )
    entries = json.loads(parse.stdout)

    payload = {
        "entries": [{"key": e["key"], "raw_text": e["raw_text"]} for e in entries],
        "cite_order": scan_data["cite_keys"],
    }
    org = subprocess.run(
        [sys.executable, str(ORGANIZE)],
        input=json.dumps(payload), capture_output=True, text=True, check=True,
    )
    actual = org.stdout
    expected = (FIXTURE / "expected/refs.bib").read_text()
    assert actual.strip() == expected.strip()
