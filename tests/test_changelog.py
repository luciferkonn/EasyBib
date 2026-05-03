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


def test_malformed_stdin_exits_cleanly(tmp_path):
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "append", str(tmp_path / "log.jsonl")],
        input="not json", capture_output=True, text=True,
    )
    assert r.returncode == 1
    assert "Traceback" not in r.stderr
    assert "invalid JSON" in r.stderr


def test_non_dict_stdin_exits_cleanly(tmp_path):
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "append", str(tmp_path / "log.jsonl")],
        input='["not", "a", "dict"]', capture_output=True, text=True,
    )
    assert r.returncode == 1
    assert "Traceback" not in r.stderr


def test_existing_ts_preserved(tmp_path):
    log = tmp_path / "log.jsonl"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "append", str(log)],
        input=json.dumps({"ts": 12345.0, "command": "/check"}),
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert json.loads(log.read_text().strip())["ts"] == 12345.0
