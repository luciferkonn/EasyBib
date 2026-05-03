# DBLP

## Endpoints

- Search: `GET https://dblp.org/search/publ/api?q=<query>&format=json&h=30`
- Condensed bibtex for a record: `GET https://dblp.org/rec/<key>.bib?param=0`
  (`param=0` is the **condensed** form — short keys, no crossref bloat.)

`dblp_fetch.py` wraps both and caches responses in `.easybib-cache/dblp/` for 7 days. Writes are atomic (`.tmp` + rename). A corrupt cache file is treated as a miss.

## Classifying a DBLP key

- `conf/...`  → `conf` (conference/workshop, peer-reviewed)
- `journals/corr/` → `corr` (arXiv preprint)
- `journals/...` → `journals` (peer-reviewed journal)
- anything else → `other`

Note the trailing slash on `journals/corr/` — venues like `journals/correlli` are not preprints.

## Version selection ("earliest")

All matching candidates are returned; the first element of the sorted list is the recommended match.

Sort key: `(year, type_rank, dblp_key)` — year wins first, type preference breaks year ties, alphabetical key as final tiebreak.

Default (`prefer_preprint = false`):
- `conf` = 0, `journals` = 1, `corr` = 2, `other` = 3.

With `--prefer-preprint`:
- `conf` = 0, `corr` = 0 (tied), `journals` = 1, `other` = 3.

This means the earliest peer-reviewed venue is usually first; preprints are still returned but ranked lower in the default mode.

## Condensed bibtex shape (what we inject)

```bibtex
@inproceedings{DBLP:conf/nips/VaswaniSPUJGKP17,
  author    = {Ashish Vaswani and ...},
  title     = {Attention is All you Need},
  booktitle = {NIPS},
  year      = {2017},
}
```

DBLP returns additional fields (`editor`, `publisher`, `pages`, `bibsource`, `biburl`); `param=0` already strips most; if any remain, leave them — do not post-process.

## Error handling

- 5xx / timeout: retry 3× with exponential backoff (1s/2s/4s).
- 4xx: do NOT retry — a 404 or 400 is not going to succeed on retry.
- 0 hits: fall through to Scholar.
- Scholar blocked/captcha: log `scholar_blocked`, fall through to WebSearch tier.
