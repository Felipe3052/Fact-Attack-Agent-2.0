## HO_E2_reference_6000 vs. HO_baseline — task B, 90 cases (90 unique)

Overrides: `REFERENCE_MAX_CHARS=6000`

| Metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Macro-F1 | 0.955 | 0.966 | +0.011 |
| Macro-F1, de-duplicated | 0.955 | 0.966 | +0.011 |
| Macro-F1, cross-language | 0.967 | 0.983 | +0.017 |
| Evidence Hit@5 | – | – | – |
| Input tokens / case | 2027 | 1758 | -13.3% |
| Output tokens / case | 55 | 60 | +10.4% |
| F1 entailment | 0.947 | 0.947 | +0.000 |
| F1 neutral | 0.967 | 0.984 | +0.017 |
| F1 contradiction | 0.952 | 0.968 | +0.015 |

- Macro-F1 change, 95 % interval (bootstrap over voting dates): [+0.011, +0.011]
- Labels fixed / broken: 1 / 0
- Cases answered through the CLI failure path: 0 / 0

Folds (date-grouped) — macro-F1 worse in 0 of 1:

| Fold | F1 before | F1 after | Change |
|---|---:|---:|---:|
| B:0 | 0.955 | 0.966 | +0.011 |

Language pairs (source→claim) — macro-F1 worse in 0 of 9:

| Pair | n | before | after | change |
|---|---:|---:|---:|---:|
| de->de | 10 | 0.886 | 0.886 | +0.000 |
| de->fr | 10 | 1.000 | 1.000 | +0.000 |
| de->it | 10 | 0.802 | 0.915 | +0.113 |
| fr->de | 10 | 1.000 | 1.000 | +0.000 |
| fr->fr | 10 | 0.915 | 0.915 | +0.000 |
| fr->it | 10 | 1.000 | 1.000 | +0.000 |
| it->de | 10 | 1.000 | 1.000 | +0.000 |
| it->fr | 10 | 1.000 | 1.000 | +0.000 |
| it->it | 10 | 1.000 | 1.000 | +0.000 |
