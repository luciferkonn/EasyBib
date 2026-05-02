import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("skills/easybib/scripts/tex_scan.py").resolve()


def run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True
    )


def test_empty_cites_detected_for_all_commands_and_placeholders():
    r = run("tests/fixtures/tex/empty_cites/main.tex")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    empties = data["empty_cites"]
    placeholders = sorted(e["placeholder"] for e in empties)
    assert placeholders == ["", "?", "TODO"]
    commands = sorted(e["command"] for e in empties)
    assert commands == ["cite", "citep", "citet"]
    for e in empties:
        assert "context_before" in e and "context_after" in e


def test_cite_keys_record_section_and_first_appearance():
    r = run("tests/fixtures/tex/sections/main.tex")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    keys = data["cite_keys"]
    first = {}
    for k in keys:
        first.setdefault(k["key"], k)
    assert first["pre"]["section"] == "__preamble__"
    assert first["a1"]["section"] == "Alpha"
    assert first["a2"]["section"] == "Alpha"
    assert first["b1"]["section"] == "Beta"
    order = [k["key"] for k in keys if k["key"] in {"a1", "a2", "b1", "b2"}]
    assert order[0] == "a1"
    assert order.index("a1") < order.index("a2")


def test_sections_recorded_in_document_order():
    r = run("tests/fixtures/tex/sections/main.tex")
    data = json.loads(r.stdout)
    assert [s["title"] for s in data["sections"]] == ["Alpha", "Beta"]
