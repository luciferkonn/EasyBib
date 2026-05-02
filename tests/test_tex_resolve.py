import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("skills/easybib/scripts/tex_resolve.py").resolve()


def run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True
    )


def test_resolve_multi_file_returns_all_tex_files():
    r = run("tests/fixtures/tex/multi_file/main.tex")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    names = sorted(Path(p).name for p in data["files"])
    assert names == ["extra.tex", "intro.tex", "main.tex", "methods.tex"]
    assert any("does_not_exist" in w for w in data["warnings"])


def test_resolve_cycle_does_not_infinite_loop():
    r = run("tests/fixtures/tex/cycle/a.tex")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert len(data["files"]) == 2
    assert any("cycle" in w.lower() or "already" in w.lower() for w in data["warnings"])
