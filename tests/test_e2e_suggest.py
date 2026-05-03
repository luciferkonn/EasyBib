import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(".").resolve()
TEX_SCAN = ROOT / "skills/easybib/scripts/tex_scan.py"
FIXTURE = ROOT / "tests/fixtures/projects/suggest_basic"


def test_empty_cites_discovered_with_contexts():
    r = subprocess.run(
        [sys.executable, str(TEX_SCAN), str(FIXTURE / "main.tex")],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(r.stdout)
    assert len(data["empty_cites"]) == 2
    contexts = [e["context_before"].lower() for e in data["empty_cites"]]
    assert any("bert" in c for c in contexts)
    assert any("transformer" in c for c in contexts)
