# Bib-Easy — Design Spec

**Date:** 2026-05-01
**Status:** Approved
**Topic:** Claude Code plugin for validating, resolving, filling, and organizing bibtex citations from DBLP.

## 1. Overview

Bib-Easy is a Claude Code plugin that helps LaTeX authors maintain correct,
DBLP-sourced bibliographies. It ships as a hybrid: one agent skill that
auto-triggers on relevant natural-language requests, plus four slash commands
for explicit invocation.

**Commands:**

- `/check` — validate every entry in `.bib` against DBLP. Replace or flag.
- `/suggest` — scan `.tex` files for empty `\cite{}` / `\citep{}` / `\citet{}`
  commands; fill them using WebSearch → DBLP → Google Scholar fallback chain.
- `/create` — create a `.bib` from scratch (or fill missing keys) based on
  cite keys present in `.tex`.
- `/organize` — reorder `.bib` entries by first-appearance section in the
  main `.tex` file, with `% === Section Name ===` comment headers.

**Design principles:**

- Deterministic work (parsing, API calls, fuzzy matching, reordering) is done
  by Python scripts. Decision logic (auto vs ask vs flag) lives in `SKILL.md`
  as natural-language rules Claude follows.
- Progressive disclosure per Agent Skills architecture: frontmatter always
  loaded (~100 tokens), `SKILL.md` body loaded on trigger (<5k tokens),
  reference docs and scripts loaded on demand.
- Safety first: atomic writes, session backups, idempotent reruns, never
  auto-delete entries.

## 2. Architecture & Repository Layout

```
bib-easy/
├── plugin.json                      # Claude Code plugin manifest
├── README.md                        # install + usage
├── LICENSE
├── skills/
│   └── bib-easy/
│       ├── SKILL.md                 # Level 2: core workflow, decision rules
│       ├── DBLP.md                  # Level 3: DBLP API reference
│       ├── MATCHING.md              # Level 3: fuzzy match algo & thresholds
│       ├── CONFIG.md                # Level 3: config schema & defaults
│       └── scripts/
│           ├── dblp_fetch.py
│           ├── scholar_fetch.py
│           ├── bib_parse.py
│           ├── tex_scan.py
│           ├── tex_resolve.py
│           ├── fuzzy_match.py
│           ├── organize_bib.py
│           ├── changelog.py
│           └── requirements.txt
├── commands/
│   ├── check.md                     # /check — thin wrapper that invokes skill
│   ├── suggest.md
│   ├── create.md
│   └── organize.md
└── tests/
    ├── fixtures/
    │   ├── bib/
    │   ├── tex/
    │   ├── projects/
    │   ├── dblp/                    # recorded DBLP JSON
    │   └── scholar/                 # recorded Scholar JSON
    └── test_*.py
```

**Level 1 (always loaded) — `SKILL.md` frontmatter:**

```yaml
---
name: bib-easy
description: Validate, resolve, fill, and organize bibtex citations from DBLP. Use when working with .bib files, empty \cite{} commands in LaTeX, or when the user asks to check, suggest, create, or organize bibliography entries.
---
```

**Level 2 — `SKILL.md` body:** the four workflows, decision trees, rules
for when to invoke scripts, when to consult reference docs, what to do on
each confidence tier.

**Level 3 — on-demand:**

- `DBLP.md` — API endpoints, query shapes, condensed-bibtex rules, version
  selection algorithm.
- `MATCHING.md` — fuzzy matching algorithm, threshold values, tie-break
  rules.
- `CONFIG.md` — full config schema and defaults.
- Scripts in `scripts/` — run via bash; their code never enters the
  context window, only their output.

## 3. Components (scripts)

| Script | Input | Output | Used by |
|---|---|---|---|
| `tex_resolve.py` | path to main `.tex` | flat list of all resolved `.tex` paths (follows `\input`/`\include`/`\subfile`) | `/suggest`, `/organize` |
| `tex_scan.py` | list of `.tex` paths | JSON: `{empty_cites: [...], cite_keys: [...], sections: [...]}`. `empty_cite` = `{file, line, col, command, placeholder, context_before, context_after}`. `cite_key` = `{key, file, line, section}` | `/suggest`, `/organize`, `/create` |
| `bib_parse.py` | path to `.bib` | JSON list of entries `{key, type, fields, raw_text, line_start, line_end}`. Preserves original raw text per entry | all four |
| `dblp_fetch.py` | query string OR DBLP key, `prefer_preprint` flag | JSON: candidates with `{dblp_key, title, authors, year, venue, type, bibtex_condensed, doi}` sorted by resolution rule | `/check`, `/suggest`, `/create` |
| `scholar_fetch.py` | query string | JSON: top candidate or `None` | `/suggest`, `/create` |
| `fuzzy_match.py` | existing entry + DBLP/Scholar candidates | scored list + top tier (`high`/`medium`/`low`/`none`) | `/check`, `/suggest`, `/create` |
| `organize_bib.py` | `.bib` entries + section-ordered cite keys | reordered `.bib` content with section headers + `% Unused` tail | `/organize` |
| `changelog.py` | action record | appends to `.bib-easy.log` (JSONL) | all four |

### Dependencies

Python ≥ 3.9. `scripts/requirements.txt`:

- `requests` — DBLP HTTP
- `scholarly` — Google Scholar
- `rapidfuzz` — fuzzy matching (MIT)
- `tomli` — config parsing on <3.11

On first `ImportError`, skill prints the install command and stops. Does not
auto-install.

## 4. Data Flow by Command

### /check

```
read .bib → bib_parse.py → for each entry:
  dblp_fetch.py (by DBLP-key / DOI / title) → fuzzy_match.py → tier
    high    → replace in-place, log
    medium  → prompt user in chat, apply choice, log
    low     → mark in .bib-easy-review.md, log
    none    → mark in .bib-easy-review.md, log
→ atomic write .bib (only if changes) → write changelog
```

### /suggest

```
tex_resolve.py → tex_scan.py (empty cites) → for each empty cite:
  1. WebSearch(context + placeholder) → candidate title/authors
  2. dblp_fetch.py → match? tier it
  3. else scholar_fetch.py → match? mark % bib-easy: source=scholar
  4. else use raw WebSearch → mark % bib-easy: source=web UNVERIFIED
     AND append to .bib-easy-review.md ("please double-check")
  routing by confidence (applies to tiers 2 & 3):
    high    → fill \cite{key}, append to .bib, log
    medium  → prompt in chat (show context + top 3), apply choice, log
    low     → flag in review file, log
→ atomic write .tex files → atomic write .bib → write changelog
```

### /create

```
if no .bib:       scan .tex → treat ALL cite keys as missing
else:             scan .tex → diff cite keys vs .bib → missing set
for each missing key:
  interpret key as hint (e.g. smith2020bert → "smith bert 2020")
  follow same fallback chain as /suggest
```

### /organize

```
tex_resolve.py
→ tex_scan.py (section-aware cite keys in first-appearance order)
→ bib_parse.py
→ organize_bib.py: group entries by first \section{} they appear under,
  entries never cited go under % Unused, write % === Section ===
  headers between groups
→ write .bib.bak (first time this session, skipped if git clean)
→ atomic write .bib → write changelog
```

Section granularity: `\section{}` only (subsections intentionally excluded
as default — configurable via `group_by`). A cite key appearing in multiple
sections goes under the section where it first appears.

## 5. DBLP & Scholar Integration

### DBLP endpoints

- **Search:** `https://dblp.org/search/publ/api?q=<query>&format=json&h=30`
- **Fetch condensed bibtex:** `https://dblp.org/rec/<key>.bib?param=0`
  (param=0 = condensed form: short keys, no crossref bloat)
- **DOI lookup:** search by DOI string, take single hit.

### Version selection ("earliest")

1. Collect hits matching canonical title within 0.95 similarity.
2. Classify by DBLP type: `conf` (conference), `journals` (journal),
   `journals/corr` (arXiv/CoRR).
3. If `prefer_preprint = false` (default): sort `conf` + `journals` ascending
   by year, pick earliest. Use `corr` only if nothing else.
4. If `prefer_preprint = true`: include `corr` in the sort.
5. Tie-break in same year: prefer `conf` over `journals`, then alphabetical
   venue key for determinism.

### Condensed bibtex shape

```bibtex
@inproceedings{DBLP:conf/nips/VaswaniSPUJGKP17,
  author    = {Ashish Vaswani and ...},
  title     = {Attention is All you Need},
  booktitle = {NIPS},
  year      = {2017},
}
```

Strip `editor`, `publisher`, `pages`, `bibsource`, `biburl`.

### Google Scholar

- Package: `scholarly` (unofficial; best-effort).
- Query: `"<title>" <first_author>` or raw context fallback.
- Compose minimal `@inproceedings`/`@article` from result.
- Key generation: `<firstauthor_lastname><year><first_significant_word_of_title>`
  lowercased, e.g. `smith2020bert`.
- Any failure (captcha, network, block) → return `None`, fall through.

### Caching & rate limiting

- DBLP: cache JSON in `.bib-easy-cache/dblp/<sha1(query)>.json`, 7-day TTL.
- Scholar: same pattern under `.bib-easy-cache/scholar/`.
- `.bib-easy-cache/` added to `.gitignore` on first run.

## 6. Configuration

Optional `.bib-easy.toml` at project root:

```toml
prefer_preprint = false
main_tex = "main.tex"                    # auto-detected if unset
placeholder_patterns = ["", "?", "TODO", "FIXME", "XXX"]
confidence_high = 0.90
confidence_medium = 0.70
group_by = ["section"]                   # /organize granularity
```

All keys optional. Defaults above apply when unset.

## 7. Artifacts Written

- `.bib` — modified in place (atomic).
- `.bib.bak` — written once per session before first destructive edit.
  **Skipped if git working tree is clean** (git is the better backup).
- `.bib-easy.log` — JSONL changelog, append-only. One record per action:
  `{ts, command, entry_key, action: "replaced"|"added"|"flagged"|"skipped"|"review_resolved", confidence, source: "dblp"|"scholar"|"web"|"cache", reason?}`.
- `.bib-easy-review.md` — human queue of low/none-confidence items. Actively
  cleaned up by subsequent runs when the underlying condition resolves (empty
  cite now filled, flagged entry now matches DBLP). Each cleanup is logged
  to `.bib-easy.log` as `review_resolved` so the audit trail persists.

## 8. Error Handling

| Failure | Behavior |
|---|---|
| DBLP 5xx / timeout | Retry 3× with exponential backoff (1s/2s/4s). Cache "failed" marker 60s. Skip entry, log `network_error`, continue. |
| DBLP zero hits | Fall through to Scholar, then WebSearch tier. |
| Scholar block/captcha | Log `scholar_blocked`. Skip Scholar for rest of run. |
| WebSearch nothing usable | Tier "none" — flag in review file. |
| Malformed `.bib` parse error | Abort before any write. Report line number. |
| `main.tex` not found | Auto-detect: scan project root and one level down for files containing `\documentclass`. If exactly one, use it. If zero or multiple, ask the user. Cache the choice in `.bib-easy.toml` as `main_tex` if the user confirms. |
| `\input{}` missing file | Warn, skip that file, continue. |
| Duplicate cite-key collision on `/create`/`/suggest` | Suffix with `a`, `b`, ... Log collision. |
| Python deps missing | Print install command, stop. No auto-install. |
| User interrupts mid-run | Changelog + atomic writes persist. Rerun is safe. |

### Idempotence

All commands safe to re-run:

- `/check` — re-runs produce no edits on already-checked entries. Cache keeps it fast.
- `/suggest` — only acts on empty placeholders; filled cites are skipped next run.
- `/create` — only acts on missing set.
- `/organize` — deterministic output; second run byte-identical.

### Dry-run

Every command supports a dry-run path. Because slash commands are markdown
prompts (not shell commands with flags), dry-run is surfaced two ways:
the command prompt accepts natural-language qualifiers like `/check dry run`
or `/check --dry-run`, and the skill recognizes either. Dry-run produces
changelog + review file but writes nothing to `.bib` / `.tex`.

## 9. Security

- Skill never executes bibtex content as code.
- WebSearch/Scholar queries are text extracted from local files only. No
  secret exfil path, but documented in README so users understand the
  boundary.
- Scripts have no network access outside DBLP, Scholar, and Claude Code's
  WebSearch tool.

## 10. Testing

### Unit tests (no network)

- `bib_parse` — round-trip fidelity (byte-identical for well-formed input),
  correct line numbers on malformed entries, preserves comments/whitespace.
- `tex_scan` — empty-cite detection across `\cite`/`\citep`/`\citet`,
  placeholder patterns, section boundary correctness, first-appearance
  ordering.
- `tex_resolve` — `\input`/`\include`/`\subfile` resolution, missing-file
  warning, circular-include guard.
- `fuzzy_match` — threshold behavior on known pairs (identical, typo,
  wrong paper).
- `organize_bib` — deterministic reordering, correct headers, `% Unused`
  tail, idempotent second run.
- `changelog` — JSONL append never corrupts existing log.

### Integration tests (mocked network)

- `dblp_fetch` — recorded DBLP responses under `tests/fixtures/dblp/`.
  Covers single match, multi-version (both `prefer_preprint` settings),
  zero results, 5xx retry path.
- `scholar_fetch` — recorded fixture + simulated block path.
- End-to-end command flows — each command run against fixture projects in
  `tests/fixtures/projects/`, all network mocked. Diff actual vs
  `expected/` subdir.

### Not in CI

- Live DBLP/Scholar calls: `make smoke` target, maintainer runs locally
  before tagging a release.
- Claude's medium-confidence chat prompts: validated manually.

### Dev tooling

- `pytest` runner, `requirements-dev.txt` separate from runtime reqs.
- `Makefile`: `make test`, `make smoke`, `make lint` (ruff).
- GitHub Actions: `make test` + `make lint` on PR. No live network in CI.

## 11. README Contents

- Install (plugin marketplace + manual git install).
- Quickstart per command with one example each.
- Config file reference.
- Troubleshooting (DBLP down, Scholar blocked, dependency issues).
- Development section pointing at `tests/` for contributors.

## 12. Open Follow-ups (post-v1)

None blocking for v1. Possible future work:

- Claim-based suggestion (beyond empty cites) for `/suggest`.
- `/export` to produce a clean `.bib` with only cited entries.
- Support for `biblatex` specifics beyond the standard bibtex subset.
