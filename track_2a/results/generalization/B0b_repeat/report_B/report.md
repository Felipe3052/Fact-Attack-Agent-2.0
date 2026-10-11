## B0b_repeat vs. B0_submission — task B, 1488 cases (1153 unique)

Overrides: `none`

| Metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Macro-F1 | 0.981 | 0.982 | +0.001 |
| Macro-F1, de-duplicated | 0.979 | 0.980 | +0.002 |
| Macro-F1, cross-language | 0.979 | 0.981 | +0.002 |
| Evidence Hit@5 | – | – | – |
| Input tokens / case | 2482 | 2482 | +0.0% |
| Output tokens / case | 56 | 56 | +0.2% |
| F1 entailment | 0.989 | 0.989 | +0.000 |
| F1 neutral | 0.983 | 0.985 | +0.002 |
| F1 contradiction | 0.972 | 0.974 | +0.002 |

- Macro-F1 change, 95 % interval (bootstrap over voting dates): [+0.000, +0.003]
- Labels fixed / broken: 2 / 0
- Cases answered through the CLI failure path: 0 / 0

Folds (date-grouped) — macro-F1 worse in 0 of 5:

| Fold | F1 before | F1 after | Change |
|---|---:|---:|---:|
| B:0 | 0.976 | 0.976 | +0.000 |
| B:1 | 0.976 | 0.976 | +0.000 |
| B:2 | 0.983 | 0.985 | +0.002 |
| B:3 | 0.985 | 0.985 | +0.000 |
| B:4 | 0.984 | 0.987 | +0.003 |

Language pairs (source→claim) — macro-F1 worse in 0 of 9:

| Pair | n | before | after | change |
|---|---:|---:|---:|---:|
| de->de | 159 | 0.966 | 0.966 | +0.000 |
| de->fr | 149 | 0.953 | 0.953 | +0.000 |
| de->it | 147 | 0.958 | 0.958 | +0.000 |
| fr->de | 184 | 0.989 | 0.995 | +0.006 |
| fr->fr | 196 | 0.990 | 0.990 | +0.000 |
| fr->it | 189 | 0.984 | 0.990 | +0.005 |
| it->de | 152 | 0.994 | 0.994 | +0.000 |
| it->fr | 152 | 0.986 | 0.986 | +0.000 |
| it->it | 160 | 1.000 | 1.000 | +0.000 |
