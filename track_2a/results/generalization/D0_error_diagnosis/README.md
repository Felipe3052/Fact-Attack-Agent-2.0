# D0 — task A error diagnosis of B0 (offline)

See `docs/independent_experiments.md`, section 6. Run from `track_2a` after `scripts/prepare_competition_cases.py`
(`.cache/gen/data`). No inference call: only the short query translations of the production retrieval are acquired
(cached under `.cache/gen/queries/diag_contexts`).

- `diag_contexts.py . <out.jsonl>` — rebuilds every task A context of B0, maps gold passages (without the vote title)
  to pages, records cited pages and Hit@5 of B0/B0b → `diag_B0.jsonl`
- `categorize.py diag_B0.jsonl` — error categories (label errors, Hit@5 misses)
- `clip_probe.py <out.jsonl>` — does the 3,000-character page window keep the gold text, with and without the claim's
  translation in the window query (translations from the cache, `MOCK_APERTUS=true`) → `clip_probe.jsonl`
