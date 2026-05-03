# Fuzzy Matching

Implemented in `fuzzy_match.py` on top of `rapidfuzz.fuzz.token_set_ratio`.

## Score

`score = 0.8 * title_sim + 0.2 * author_last_name_jaccard`

- Titles are lowercased, whitespace-collapsed, then compared with `token_set_ratio` (0–1).
- Authors are reduced to last names (both `"First Last"` and `"Last, First"` formats supported), lowercased, compared by Jaccard overlap.

## Tiers

| Tier    | Score range | Action                                  |
|---------|-------------|-----------------------------------------|
| high    | ≥ 0.90      | auto-replace / auto-fill                |
| medium  | ≥ 0.70      | ask user in chat, show top 3 candidates |
| low     | > 0.0       | flag in `.easybib-review.md`            |
| none    | no cands    | flag in `.easybib-review.md`            |

Thresholds are config-overridable via `confidence_high` / `confidence_medium` in `.easybib.toml`. If `high < medium`, the script exits 2 with an error.

## Tie-breaking

When sorted score is a tie across multiple candidates, `dblp_fetch.py` has already sorted by year → type preference → DBLP key, so `scored[0]` is deterministic.
