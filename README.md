# EasyBib

Claude Code plugin that validates, resolves, fills, and organizes bibtex citations from DBLP.

## Install

```bash
claude plugins install <this-repo-url>
```

## Quickstart

- `/check` — validate every entry in `.bib` against DBLP.
- `/suggest` — fill empty `\cite{}` in `.tex`.
- `/create` — create or fill a `.bib` from cite keys in `.tex`.
- `/organize` — reorder `.bib` by first-appearance section.

## Configuration

Optional `.easybib.toml`. See `skills/easybib/CONFIG.md`.

## Development

```bash
make install-dev
make test
make lint
```
