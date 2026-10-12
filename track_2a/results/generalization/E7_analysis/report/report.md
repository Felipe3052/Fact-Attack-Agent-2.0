## E7_compact vs. E7_baseline_fresh — task A, 1488 cases (1149 unique)

Overrides: `A_RELATION_PROMPT=false A_SKILL_PROMPT=false A_COMPACT_PROMPT=true`

| Metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Macro-F1 | 0.942 | 0.949 | +0.007 |
| Macro-F1, de-duplicated | 0.943 | 0.953 | +0.010 |
| Macro-F1, cross-language | 0.943 | 0.949 | +0.005 |
| Evidence Hit@5 | 0.867 | 0.881 | +0.014 |
| Input tokens / case | 3818 | 3915 | +2.5% |
| Output tokens / case | 58 | 60 | +4.0% |
| F1 entailment | 0.932 | 0.939 | +0.007 |
| F1 neutral | 0.958 | 0.969 | +0.010 |
| F1 contradiction | 0.935 | 0.940 | +0.005 |

- Macro-F1 change, 95 % interval (bootstrap over voting dates): [-0.001, +0.018]
- Labels fixed / broken: 22 / 11; evidence fixed / broken: 23 / 9
- Cases answered through the CLI failure path: 0 / 0

Folds (date-grouped) — macro-F1 worse in 3 of 5:

| Fold | F1 before | F1 after | Change | Hit@5 before | Hit@5 after |
|---|---:|---:|---:|---:|---:|
| A:0 | 0.982 | 0.971 | -0.011 | 0.921 | 0.908 |
| A:1 | 0.929 | 0.950 | +0.021 | 0.858 | 0.879 |
| A:2 | 0.963 | 0.980 | +0.017 | 0.893 | 0.904 |
| A:3 | 0.919 | 0.919 | -0.000 | 0.858 | 0.874 |
| A:4 | 0.919 | 0.919 | -0.000 | 0.809 | 0.838 |

Language pairs (source→claim) — macro-F1 worse in 2 of 9:

| Pair | n | before | after | change |
|---|---:|---:|---:|---:|
| de->de | 159 | 0.920 | 0.960 | +0.040 |
| de->fr | 149 | 0.893 | 0.900 | +0.007 |
| de->it | 147 | 0.939 | 0.924 | -0.014 |
| fr->de | 184 | 0.945 | 0.967 | +0.022 |
| fr->fr | 196 | 0.933 | 0.934 | +0.000 |
| fr->it | 189 | 0.958 | 0.968 | +0.010 |
| it->de | 152 | 0.953 | 0.953 | -0.000 |
| it->fr | 152 | 0.966 | 0.967 | +0.001 |
| it->it | 160 | 0.960 | 0.960 | +0.000 |
