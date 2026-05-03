import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(".").resolve()
TEX_SCAN = ROOT / "skills/easybib/scripts/tex_scan.py"
FIXTURE = ROOT / "tests/fixtures/projects/create_from_scratch"


def test_missing_keys_identified_when_no_bib():
    r = subprocess.run(
        [sys.executable, str(TEX_SCAN), str(FIXTURE / "main.tex")],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(r.stdout)
    keys = sorted({k["key"] for k in data["cite_keys"]})
    assert keys == ["alpha", "beta"]
