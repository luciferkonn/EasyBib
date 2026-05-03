# Configuration

Place `.easybib.toml` at the project root. All keys optional.

```toml
prefer_preprint      = false
main_tex             = "main.tex"                   # auto-detected if unset
placeholder_patterns = ["", "?", "TODO", "FIXME", "XXX"]
confidence_high      = 0.90
confidence_medium    = 0.70
group_by             = ["section"]                  # /organize granularity
```

Loaded by `config.py load <project_dir>`. Unknown keys are silently ignored (no warning).

## Notes

- `main_tex` is relative to the project root. If set, `/suggest`, `/create`, `/organize` use it without auto-detection.
- `placeholder_patterns` controls which `\cite{...}` values count as empty.
- `group_by` is currently a list for forward compatibility; only `["section"]` is implemented.
- A malformed `.easybib.toml` causes `config.py` to exit 1 with a clean error — the skill should stop and surface the message.
