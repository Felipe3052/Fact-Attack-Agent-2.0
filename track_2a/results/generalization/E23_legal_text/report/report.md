## E23_legal_text vs. E12_part_context — task A, 1488 cases (1149 unique)

Overrides: `none`

| Metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Macro-F1 | 0.968 | 0.974 | +0.007 |
| Macro-F1, de-duplicated | 0.965 | 0.968 | +0.004 |
| Macro-F1, cross-language | 0.971 | 0.981 | +0.009 |
| Evidence Hit@5 | 0.975 | 0.983 | +0.008 |
| Input tokens / case | 1750 | 1791 | +2.3% |
| Output tokens / case | 59 | 59 | +1.1% |
| F1 entailment | 0.975 | 0.979 | +0.004 |
| F1 neutral | 0.972 | 0.981 | +0.009 |
| F1 contradiction | 0.956 | 0.963 | +0.007 |

- Macro-F1 change, 95 % interval (bootstrap over voting dates): [+0.002, +0.012]
- Labels fixed / broken: 12 / 2; evidence fixed / broken: 8 / 0
- Cases answered through the CLI failure path: 0 / 0

Folds (date-grouped) — macro-F1 worse in 0 of 5:

| Fold | F1 before | F1 after | Change | Hit@5 before | Hit@5 after |
|---|---:|---:|---:|---:|---:|
| A:0 | 0.975 | 0.980 | +0.005 | 0.967 | 0.974 |
| A:1 | 0.954 | 0.965 | +0.011 | 0.953 | 0.974 |
| A:2 | 0.973 | 0.980 | +0.007 | 0.973 | 0.985 |
| A:3 | 0.978 | 0.978 | +0.000 | 0.995 | 0.995 |
| A:4 | 0.958 | 0.968 | +0.010 | 0.985 | 0.985 |

Language pairs (source→claim) — macro-F1 worse in 1 of 9:

| Pair | n | before | after | change |
|---|---:|---:|---:|---:|
| de->de | 159 | 0.939 | 0.946 | +0.006 |
| de->fr | 149 | 0.933 | 0.947 | +0.014 |
| de->it | 147 | 0.958 | 0.986 | +0.028 |
| fr->de | 184 | 0.995 | 0.995 | +0.000 |
| fr->fr | 196 | 0.948 | 0.959 | +0.010 |
| fr->it | 189 | 0.990 | 0.990 | +0.000 |
| it->de | 152 | 0.968 | 0.981 | +0.013 |
| it->fr | 152 | 0.974 | 0.980 | +0.006 |
| it->it | 160 | 0.994 | 0.981 | -0.012 |
