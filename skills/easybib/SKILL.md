---
name: easybib
description: Validate, resolve, fill, and organize bibtex citations from DBLP. Use when working with .bib files, empty \cite{} commands in LaTeX, or when the user asks to check, suggest, create, or organize bibliography entries.
---

# EasyBib

Maintain LaTeX bibliographies using DBLP as the source of truth, with Google Scholar and WebSearch as fallbacks. Supports four workflows via slash commands (`/check`, `/suggest`, `/create`, `/organize`) and also triggers on natural-language requests matching the description.

## General operating rules

- **Dependencies:** If any script exits with `ModuleNotFoundError`, print `pip install -r skills/easybib/scripts/requirements.txt` and stop. Do not auto-install.
- **Config:** Before any workflow, run `python skills/easybib/scripts/config.py load .` and honor the returned values.
- **Backups:** Before the first write to `.bib` or any `.tex` in a session, check `git status --porcelain`. If clean, skip the `.bak`. If dirty, write `<path>.bak` once (never overwrite an existing `.bak` from this session).
- **Atomic writes:** always write via a `.tmp` + rename. The `bib_parse.py write` and `organize_bib.py` flows already do this.
- **Changelog:** every action (`replaced`, `added`, `flagged`, `skipped`, `review_resolved`, `network_error`) goes to `.easybib.log` via `python skills/easybib/scripts/changelog.py append .easybib.log`.
- **Review file:** `.easybib-review.md` holds human-queue items. At the start of every workflow, scan it and remove entries whose condition has resolved; log each removal as `review_resolved`.
- **Dry-run:** if the user says "dry run" or passes `--dry-run`, run the workflow but skip `.bib`/`.tex` writes. Still write changelog and review file.

## Confidence tiers (applied to DBLP or Scholar candidates)

- `high` (≥ 0.90): replace/fill automatically.
- `medium` (≥ 0.70): show the user the entry + top 3 candidates inline, wait for their choice.
- `low` / `none`: flag in `.easybib-review.md`, leave the `.bib`/`.tex` untouched.

## Workflow: /check

1. Parse `.bib` with `bib_parse.py parse <bib>`. Abort with user-visible error on parse failure.
2. For each entry:
   a. If the entry key starts with `DBLP:`, run `dblp_fetch.py bibtex <key>` — that's the canonical form; compare and replace if different.
   b. Else query `dblp_fetch.py search "<title> <first_author>" [--prefer-preprint]`. Pass the result plus the entry to `fuzzy_match.py` (stdin JSON).
   c. Route by tier (above).
3. Write `.bib.bak` if needed, atomic write updated `.bib`, log every action.

## Workflow: /suggest

1. Resolve main `.tex`:
   - If `main_tex` set in config, use it.
   - Else scan project root + one level deep for `.tex` containing `\documentclass`. If exactly one, use it; else ask the user.
2. Run `tex_scan.py <main.tex> <placeholders...>`. If no empty cites, report and exit.
3. For each empty cite (fallback chain):
   a. `WebSearch` with `<context_before> <context_after> <placeholder>` → extract likely title/first-author.
   b. `dblp_fetch.py search "<title> <author>"` → `fuzzy_match.py` → tier. On `high`/`medium`, stop the chain; on `low`/`none`, fall through.
   c. `scholar_fetch.py "<title> <author>"`. If `found`, append with `% easybib: source=scholar` comment; tier using `fuzzy_match.py` the same way.
   d. Else use the raw WebSearch result. Append `% easybib: source=web UNVERIFIED`. Always flag in review file.
4. On accept (high auto, medium user-approved):
   - Replace `\cite{<placeholder>}` with `\cite{<key>}` in the `.tex` file.
   - Append the fetched bibtex to `.bib` (dedupe by key; suffix `a`, `b`, … on collision).
   - Log.

## Workflow: /create

1. If no `.bib` exists, create an empty one.
2. Resolve main `.tex`, run `tex_scan.py`. Gather all cite keys (non-empty).
3. Diff against `.bib` keys → `missing` set.
4. For each missing key, interpret as a hint (regex split on letters/digits, e.g. `smith2020bert` → `"smith 2020 bert"`) and run the same fallback chain as `/suggest` (tiered routing).
5. Append accepted entries to `.bib`.

## Workflow: /organize

1. Resolve main `.tex`, run `tex_scan.py`. Take the `cite_keys` list (ordered by first-appearance) and `.bib` entries.
2. Pipe `{"entries": [...], "cite_order": [...]}` into `organize_bib.py`.
3. Write `.bib.bak` if needed, atomic write the new `.bib`.

## When to read more

- DBLP API quirks and version selection → `DBLP.md`.
- Fuzzy-match thresholds and tie-breaking → `MATCHING.md`.
- Full config schema → `CONFIG.md`.
