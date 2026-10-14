## E25_s_role vs. E23_legal_text — task A, 1488 cases (1149 unique)

Overrides: `A_PROMPT_DROP=role`

| Metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Macro-F1 | 0.974 | 0.977 | +0.003 |
| Macro-F1, de-duplicated | 0.968 | 0.971 | +0.003 |
| Macro-F1, cross-language | 0.981 | 0.982 | +0.001 |
| Evidence Hit@5 | 0.983 | 0.980 | -0.003 |
| Input tokens / case | 1791 | 1757 | -1.9% |
| Output tokens / case | 59 | 59 | -1.4% |
| F1 entailment | 0.979 | 0.979 | +0.000 |
| F1 neutral | 0.981 | 0.982 | +0.001 |
| F1 contradiction | 0.963 | 0.970 | +0.007 |

- Macro-F1 change, 95 % interval (bootstrap over voting dates): [-0.001, +0.006]
- Labels fixed / broken: 5 / 1; evidence fixed / broken: 1 / 4
- Cases answered through the CLI failure path: 0 / 0

Folds (date-grouped) — macro-F1 worse in 1 of 5:

| Fold | F1 before | F1 after | Change | Hit@5 before | Hit@5 after |
|---|---:|---:|---:|---:|---:|
| A:0 | 0.980 | 0.980 | +0.000 | 0.974 | 0.974 |
| A:1 | 0.965 | 0.971 | +0.006 | 0.974 | 0.968 |
| A:2 | 0.980 | 0.980 | +0.000 | 0.985 | 0.985 |
| A:3 | 0.978 | 0.974 | -0.004 | 0.995 | 0.989 |
| A:4 | 0.968 | 0.978 | +0.010 | 0.985 | 0.980 |

Language pairs (source→claim) — macro-F1 worse in 0 of 9:

| Pair | n | before | after | change |
|---|---:|---:|---:|---:|
| de->de | 159 | 0.946 | 0.947 | +0.001 |
| de->fr | 149 | 0.947 | 0.947 | +0.000 |
| de->it | 147 | 0.986 | 0.986 | +0.000 |
| fr->de | 184 | 0.995 | 0.995 | +0.000 |
| fr->fr | 196 | 0.959 | 0.959 | +0.000 |
| fr->it | 189 | 0.990 | 0.990 | +0.000 |
| it->de | 152 | 0.981 | 0.987 | +0.006 |
| it->fr | 152 | 0.980 | 0.980 | +0.000 |
| it->it | 160 | 0.981 | 1.000 | +0.019 |
