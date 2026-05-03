import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("skills/easybib/scripts/changelog.py").resolve()


def test_append_writes_one_line_per_record(tmp_path):
    log = tmp_path / ".easybib.log"
    rec1 = {"command": "/check", "action": "replaced", "entry_key": "k1"}
    rec2 = {"command": "/check", "action": "flagged", "entry_key": "k2"}
    for rec in (rec1, rec2):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "append", str(log)],
            input=json.dumps(rec), capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
    lines = log.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["entry_key"] == "k1"
    assert json.loads(lines[1])["entry_key"] == "k2"
    assert "ts" in json.loads(lines[0])
