# E6 — evidence composition replay (offline, rejected)

See `docs/independent_experiments.md`, section 6. Run from `track_2a`; no API call, labels and citations fixed.

- `evidence_replay.py` — Hit@5 of four compositions (3/2, 2/3, 1/4, 0/5 whole pages / blocks) on B0's citations → `evidence_replay.json`
- `e6_audit.py <run>` — production vs 0/5 per case, incl. whether each hit matches the passage body or only the vote
  title → `audit_<run>.json`; printed summaries in `audit_summary.txt`
