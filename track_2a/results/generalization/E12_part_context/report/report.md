## E12_section_route vs. E7_compact — task A, 1488 cases (1149 unique)

Overrides: `SECTION_ROUTE=true`

| Metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Macro-F1 | 0.949 | 0.968 | +0.018 |
| Macro-F1, de-duplicated | 0.953 | 0.965 | +0.012 |
| Macro-F1, cross-language | 0.949 | 0.971 | +0.023 |
| Evidence Hit@5 | 0.881 | 0.975 | +0.094 |
| Input tokens / case | 3915 | 1750 | -55.3% |
| Output tokens / case | 60 | 59 | -2.6% |
| F1 entailment | 0.939 | 0.975 | +0.035 |
| F1 neutral | 0.969 | 0.972 | +0.004 |
| F1 contradiction | 0.940 | 0.956 | +0.016 |

- Macro-F1 change, 95 % interval (bootstrap over voting dates): [+0.005, +0.035]
- Labels fixed / broken: 56 / 29; evidence fixed / broken: 110 / 17
- Noise floor (baseline run twice, 1488 cases): labels 11 / 22, evidence 9 / 23
- Cases answered through the CLI failure path: 0 / 0

Folds (date-grouped) — macro-F1 worse in 1 of 5:

| Fold | F1 before | F1 after | Change | Hit@5 before | Hit@5 after |
|---|---:|---:|---:|---:|---:|
| A:0 | 0.971 | 0.975 | +0.004 | 0.908 | 0.967 |
| A:1 | 0.950 | 0.954 | +0.004 | 0.879 | 0.953 |
| A:2 | 0.980 | 0.973 | -0.007 | 0.904 | 0.973 |
| A:3 | 0.919 | 0.978 | +0.059 | 0.874 | 0.995 |
| A:4 | 0.919 | 0.958 | +0.040 | 0.838 | 0.985 |

Language pairs (source→claim) — macro-F1 worse in 1 of 9:

| Pair | n | before | after | change |
|---|---:|---:|---:|---:|
| de->de | 159 | 0.960 | 0.939 | -0.021 |
| de->fr | 149 | 0.900 | 0.933 | +0.033 |
| de->it | 147 | 0.924 | 0.958 | +0.033 |
| fr->de | 184 | 0.967 | 0.995 | +0.027 |
| fr->fr | 196 | 0.934 | 0.948 | +0.015 |
| fr->it | 189 | 0.968 | 0.990 | +0.022 |
| it->de | 152 | 0.953 | 0.968 | +0.015 |
| it->fr | 152 | 0.967 | 0.974 | +0.007 |
| it->it | 160 | 0.960 | 0.994 | +0.033 |
