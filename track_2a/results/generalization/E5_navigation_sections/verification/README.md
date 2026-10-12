# E5 verification (offline)

- `e5_proto.py` — prototype of the label rule; it gives the same labels as the implementation on all 3,241 pages
- `e5_verify.py <dir>` (on branch `exp/e5-navigation-sections`; `<dir>` holds a copy of `D0_error_diagnosis/diag_B0.jsonl`) — per case: E5 Hit@5, context with E5 labels vs B0 (same translations, `MOCK_APERTUS=true`),
  label transitions between parse cache versions 7 and 8 → `e5_verify.jsonl`
- `finish_scoring.py E5_navigation_sections A` — the scoring steps of `run_decision.py`, re-run on the unchanged
  predictions after the scoring step had crashed on a cp1252 read (now fixed in `compare_competition_runs.load`)
