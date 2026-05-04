import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("skills/easybib/scripts/organize_bib.py").resolve()


def run(payload):
    r = subprocess.run(
        [sys.executable, str(SCRIPT)], input=json.dumps(payload),
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout


def entries():
    return [
        {"key": "a1", "raw_text": "@article{a1, title={A1}, year={2020}}"},
        {"key": "a2", "raw_text": "@article{a2, title={A2}, year={2020}}"},
        {"key": "b1", "raw_text": "@article{b1, title={B1}, year={2020}}"},
        {"key": "unused", "raw_text": "@article{unused, title={X}, year={2020}}"},
    ]


def cite_order():
    return [
        {"key": "a1", "section": "Alpha"},
        {"key": "a2", "section": "Alpha"},
        {"key": "b1", "section": "Beta"},
    ]


def test_groups_entries_under_section_headers():
    out = run({"entries": entries(), "cite_order": cite_order()})
    assert "% === Alpha ===" in out
    assert "% === Beta ===" in out
    assert out.index("% === Alpha ===") < out.index("@article{a1")
    assert out.index("@article{a1") < out.index("% === Beta ===")
    assert out.index("% === Beta ===") < out.index("@article{b1")


def test_unused_entries_go_under_unused_header():
    out = run({"entries": entries(), "cite_order": cite_order()})
    assert "% === Unused ===" in out
    assert out.index("% === Unused ===") < out.index("@article{unused")


def test_idempotent_second_run_byte_identical():
    out1 = run({"entries": entries(), "cite_order": cite_order()})
    reparsed = [
        {"key": e["key"], "raw_text": e["raw_text"]}
        for e in entries()
    ]
    out2 = run({"entries": reparsed, "cite_order": cite_order()})
    assert out1 == out2


def test_preamble_section_uses_preamble_header():
    out = run({
        "entries": [{"key": "p", "raw_text": "@article{p, year={2020}}"}],
        "cite_order": [{"key": "p", "section": "__preamble__"}],
    })
    assert "% === Preamble ===" in out


def test_malformed_stdin_exits_cleanly():
    r = subprocess.run(
        [sys.executable, str(SCRIPT)], input="not json",
        capture_output=True, text=True,
    )
    assert r.returncode == 2
    assert "Traceback" not in r.stderr


def test_missing_required_key_exits_cleanly():
    r = subprocess.run(
        [sys.executable, str(SCRIPT)], input=json.dumps({"entries": []}),
        capture_output=True, text=True,
    )
    assert r.returncode == 2
    assert "Traceback" not in r.stderr
