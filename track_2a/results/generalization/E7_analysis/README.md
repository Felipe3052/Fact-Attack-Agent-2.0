# E7 — compact task A prompt (`A_COMPACT_PROMPT`), paired full evaluation

Runs: `../E7_baseline_fresh` (all prompt switches off) and `../E7_compact` (`A_COMPACT_PROMPT=true`), 1,488 task A
cases each, commit `2bae8e7` (switch from `5907dd3`), translation cache of the D0 reconstruction (read only, 973/973
cross-language queries cached, hash identical before and after), 4 workers, submission defaults otherwise.

- `preflight_prompt_inputs.jsonl` — hashes of the NLI inputs (claim + passages) from a mock dry run without endpoint;
  both runs match it in 1,488/1,488 cases (no texts stored)
- `analyze_full_eval.py --data <pinned dataset>` → `full_eval_analysis.json` (folds, dates, paired transitions,
  date bootstrap, leave-one-date-out, score scenarios); gold labels/passages are read from the dataset, never committed
- `report/` — `scripts/report_decision.py` (de-duplicated F1, language pairs, date bootstrap)

Reproduce (from `track_2a`): prepare the pinned dataset with `scripts/prepare_competition_cases.py --version v1.1
--scope all --download-booklets --output .cache/gen/data`, then `scripts/run_decision.py --data <dataset> --task A
--name <run> --query-cache-dir <cache> --set A_RELATION_PROMPT=false --set A_SKILL_PROMPT=false --set A_COMPACT_PROMPT=<false|true>`
with `PROMPT_INPUT_JOURNAL_PATH=<run>/prompt_inputs.jsonl`.
