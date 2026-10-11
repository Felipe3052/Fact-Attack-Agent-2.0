## B0b_repeat vs. B0_submission — task A, 1488 cases (1149 unique)

Overrides: `none`

| Metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Macro-F1 | 0.943 | 0.945 | +0.002 |
| Macro-F1, de-duplicated | 0.944 | 0.947 | +0.003 |
| Macro-F1, cross-language | 0.943 | 0.945 | +0.002 |
| Evidence Hit@5 | 0.869 | 0.870 | +0.001 |
| Input tokens / case | 3866 | 3867 | +0.0% |
| Output tokens / case | 76 | 76 | -0.2% |
| F1 entailment | 0.933 | 0.935 | +0.002 |
| F1 neutral | 0.958 | 0.960 | +0.002 |
| F1 contradiction | 0.936 | 0.938 | +0.002 |

- Macro-F1 change, 95 % interval (bootstrap over voting dates): [+0.000, +0.006]
- Labels fixed / broken: 3 / 0; evidence fixed / broken: 4 / 3
- Cases answered through the CLI failure path: 0 / 0

Folds (date-grouped) — macro-F1 worse in 0 of 5:

| Fold | F1 before | F1 after | Change | Hit@5 before | Hit@5 after |
|---|---:|---:|---:|---:|---:|
| A:0 | 0.977 | 0.987 | +0.010 | 0.914 | 0.921 |
| A:1 | 0.932 | 0.932 | +0.000 | 0.868 | 0.868 |
| A:2 | 0.966 | 0.966 | +0.000 | 0.893 | 0.893 |
| A:3 | 0.919 | 0.919 | +0.000 | 0.852 | 0.863 |
| A:4 | 0.919 | 0.922 | +0.003 | 0.819 | 0.809 |

Language pairs (source→claim) — macro-F1 worse in 0 of 9:

| Pair | n | before | after | change |
|---|---:|---:|---:|---:|
| de->de | 159 | 0.934 | 0.934 | +0.000 |
| de->fr | 149 | 0.893 | 0.893 | +0.000 |
| de->it | 147 | 0.939 | 0.939 | +0.000 |
| fr->de | 184 | 0.940 | 0.945 | +0.005 |
| fr->fr | 196 | 0.933 | 0.938 | +0.005 |
| fr->it | 189 | 0.963 | 0.963 | +0.000 |
| it->de | 152 | 0.953 | 0.953 | +0.000 |
| it->fr | 152 | 0.966 | 0.973 | +0.007 |
| it->it | 160 | 0.954 | 0.954 | +0.000 |
