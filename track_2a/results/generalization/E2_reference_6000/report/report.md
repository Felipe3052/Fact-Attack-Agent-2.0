## E2_reference_6000 vs. B0_submission — task B, 1488 cases (1153 unique)

Overrides: `REFERENCE_MAX_CHARS=6000`

| Metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Macro-F1 | 0.981 | 0.984 | +0.003 |
| Macro-F1, de-duplicated | 0.979 | 0.983 | +0.004 |
| Macro-F1, cross-language | 0.979 | 0.984 | +0.005 |
| Evidence Hit@5 | – | – | – |
| Input tokens / case | 2482 | 1732 | -30.2% |
| Output tokens / case | 56 | 62 | +10.3% |
| F1 entailment | 0.989 | 0.987 | -0.002 |
| F1 neutral | 0.983 | 0.990 | +0.007 |
| F1 contradiction | 0.972 | 0.977 | +0.005 |

- Macro-F1 change, 95 % interval (bootstrap over voting dates): [-0.002, +0.008]
- Labels fixed / broken: 9 / 4
- Noise floor (baseline run twice, 1488 cases): labels 2 / 0
- Cases answered through the CLI failure path: 0 / 0

Folds (date-grouped) — macro-F1 worse in 1 of 5:

| Fold | F1 before | F1 after | Change |
|---|---:|---:|---:|
| B:0 | 0.976 | 0.987 | +0.010 |
| B:1 | 0.976 | 0.968 | -0.007 |
| B:2 | 0.983 | 0.990 | +0.007 |
| B:3 | 0.985 | 0.989 | +0.004 |
| B:4 | 0.984 | 0.987 | +0.003 |

Language pairs (source→claim) — macro-F1 worse in 1 of 9:

| Pair | n | before | after | change |
|---|---:|---:|---:|---:|
| de->de | 159 | 0.966 | 0.966 | +0.000 |
| de->fr | 149 | 0.953 | 0.967 | +0.013 |
| de->it | 147 | 0.958 | 0.972 | +0.014 |
| fr->de | 184 | 0.989 | 0.995 | +0.006 |
| fr->fr | 196 | 0.990 | 0.990 | +0.000 |
| fr->it | 189 | 0.984 | 0.995 | +0.010 |
| it->de | 152 | 0.994 | 0.994 | +0.000 |
| it->fr | 152 | 0.986 | 0.972 | -0.014 |
| it->it | 160 | 1.000 | 1.000 | +0.000 |
