# EasyBib

Claude Code plugin that keeps LaTeX bibliographies correct and tidy. Uses DBLP as the source of truth; falls back to Google Scholar and WebSearch only when DBLP has no match. Entries sourced outside DBLP are always flagged for review.

## Install

Inside Claude Code, add this repo as a plugin marketplace, then install the plugin:

```
/plugin marketplace add luciferkonn/EasyBib
/plugin install easybib@bib-easy
```

Python 3.9+ required. On first run, if dependencies are missing you'll be told to run:

```bash
pip install -r skills/easybib/scripts/requirements.txt
```

## Commands

### `/check`

Validates every entry in `.bib` against DBLP. High-confidence matches are replaced in place; medium-confidence matches prompt you for a decision; low/no-confidence entries get flagged in `.easybib-review.md`.

### `/suggest`

Scans `.tex` files for empty cite commands (`\cite{}`, `\citep{}`, `\citet{}` and configurable placeholders like `TODO`, `?`, `FIXME`, `XXX`). For each, does WebSearch → DBLP → Scholar → raw-web, routes by confidence.

### `/create`

Creates `.bib` if missing, or fills any cite keys present in `.tex` but absent from `.bib`. Uses the same fallback chain as `/suggest`.

### `/organize`

Reorders `.bib` entries to match the first-appearance section order of your main `.tex`. Inserts `% === Section Name ===` headers. Never-cited entries go under `% === Unused ===` — nothing is deleted.

All commands accept `--dry-run` (or the phrase "dry run") for a no-write preview.

## Configuration

Optional `.easybib.toml` at the project root:

```toml
prefer_preprint      = false
main_tex             = "main.tex"
placeholder_patterns = ["", "?", "TODO", "FIXME", "XXX"]
confidence_high      = 0.90
confidence_medium    = 0.70
group_by             = ["section"]
```

See `skills/easybib/CONFIG.md` for the full schema.

## Artifacts

- `.bib.bak` — one-time backup written before the first destructive edit in a session, **only if git working tree is dirty**.
- `.easybib.log` — JSONL audit trail.
- `.easybib-review.md` — human queue of items needing attention. Actively cleaned up as conditions resolve.
- `.easybib-cache/` — 7-day TTL cache of DBLP and Scholar responses. Added to `.gitignore`.

## Troubleshooting

- **DBLP unreachable**: `.easybib.log` will show `network_error`. Rerun later; cached responses are still used.
- **Scholar blocked / captcha**: logged as `scholar_blocked`; the skill falls through to raw WebSearch and flags the result. Retry from a different network.
- **Dependencies missing**: see install instructions above.
- **Wrong main `.tex` detected**: set `main_tex` in `.easybib.toml`.

## Development

```bash
make install-dev
make test      # unit + e2e (no network)
make lint
make smoke     # live DBLP/Scholar, run locally before tagging
```

Tests use recorded fixtures under `tests/fixtures/` for all network calls.

## Security notes

- The skill never evaluates `.bib` content as code.
- Queries to WebSearch/Scholar are text extracted from your local `.tex` and `.bib` files. Treat this like any other tool with network access: review the diff before committing.
