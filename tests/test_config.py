import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("skills/easybib/scripts/config.py").resolve()


def test_defaults_when_no_file(tmp_path):
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "load", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    cfg = json.loads(r.stdout)
    assert cfg["prefer_preprint"] is False
    assert cfg["confidence_high"] == 0.90
    assert cfg["confidence_medium"] == 0.70
    assert cfg["placeholder_patterns"] == ["", "?", "TODO", "FIXME", "XXX"]
    assert cfg["group_by"] == ["section"]


def test_overrides_from_toml(tmp_path):
    (tmp_path / ".easybib.toml").write_text(
        "prefer_preprint = true\nconfidence_high = 0.95\n"
    )
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "load", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    cfg = json.loads(r.stdout)
    assert cfg["prefer_preprint"] is True
    assert cfg["confidence_high"] == 0.95
    assert cfg["confidence_medium"] == 0.70
