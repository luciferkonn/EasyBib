import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("skills/easybib/scripts/bib_parse.py").resolve()


def run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True
    )


def test_parse_clean_bib_returns_two_entries():
    result = run(["parse", "tests/fixtures/bib/clean.bib"])
    assert result.returncode == 0, result.stderr
    entries = json.loads(result.stdout)
    assert len(entries) == 2
    keys = [e["key"] for e in entries]
    assert keys == [
        "DBLP:conf/nips/VaswaniSPUJGKP17",
        "DBLP:journals/corr/DevlinCLT18",
    ]
    assert entries[0]["type"] == "inproceedings"
    assert entries[0]["fields"]["year"] == "2017"
    assert "Attention is All you Need" in entries[0]["fields"]["title"]
    assert entries[0]["line_start"] >= 1
    assert entries[0]["line_end"] > entries[0]["line_start"]
    assert entries[0]["raw_text"].startswith("@inproceedings{")


def test_parse_clean_bib_raw_text_appears_in_original():
    result = run(["parse", "tests/fixtures/bib/clean.bib"])
    entries = json.loads(result.stdout)
    original = Path("tests/fixtures/bib/clean.bib").read_text()
    for entry in entries:
        assert entry["raw_text"].strip() in original


def test_parse_malformed_bib_reports_line():
    result = run(["parse", "tests/fixtures/bib/malformed.bib"])
    assert result.returncode != 0
    assert "line" in result.stderr.lower()
    assert "broken_entry" in result.stderr or "6" in result.stderr or "7" in result.stderr


def test_quoted_string_braces_do_not_break_entry_boundary():
    result = run(["parse", "tests/fixtures/bib/quoted_brace.bib"])
    assert result.returncode == 0, result.stderr
    entries = json.loads(result.stdout)
    assert len(entries) == 1
    assert entries[0]["fields"]["year"] == "2020"
    assert "has a } here" in entries[0]["fields"]["note"]


def test_string_and_comment_directives_are_skipped():
    result = run(["parse", "tests/fixtures/bib/with_string.bib"])
    assert result.returncode == 0, result.stderr
    entries = json.loads(result.stdout)
    assert len(entries) == 1
    assert entries[0]["key"] == "realentry"
