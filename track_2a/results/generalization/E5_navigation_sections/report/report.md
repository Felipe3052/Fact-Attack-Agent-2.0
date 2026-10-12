## E5_navigation_sections vs. B0_submission — task A, 1488 cases (1149 unique)

Overrides: `none`

| Metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Macro-F1 | 0.943 | 0.945 | +0.002 |
| Macro-F1, de-duplicated | 0.944 | 0.946 | +0.002 |
| Macro-F1, cross-language | 0.943 | 0.945 | +0.002 |
| Evidence Hit@5 | 0.869 | 0.874 | +0.005 |
| Input tokens / case | 3866 | 3868 | +0.1% |
| Output tokens / case | 76 | 77 | +0.4% |
| F1 entailment | 0.933 | 0.934 | +0.001 |
| F1 neutral | 0.958 | 0.956 | -0.003 |
| F1 contradiction | 0.936 | 0.944 | +0.008 |

- Macro-F1 change, 95 % interval (bootstrap over voting dates): [-0.002, +0.007]
- Labels fixed / broken: 8 / 5; evidence fixed / broken: 21 / 16
- Noise floor (baseline run twice, 1488 cases): labels 3 / 0, evidence 4 / 3
- Cases answered through the CLI failure path: 0 / 0

Folds (date-grouped) — macro-F1 worse in 3 of 5:

| Fold | F1 before | F1 after | Change | Hit@5 before | Hit@5 after |
|---|---:|---:|---:|---:|---:|
| A:0 | 0.977 | 0.976 | -0.001 | 0.914 | 0.895 |
| A:1 | 0.932 | 0.943 | +0.011 | 0.868 | 0.884 |
| A:2 | 0.966 | 0.963 | -0.003 | 0.893 | 0.908 |
| A:3 | 0.919 | 0.919 | -0.000 | 0.852 | 0.885 |
| A:4 | 0.919 | 0.922 | +0.004 | 0.819 | 0.794 |

Language pairs (source→claim) — macro-F1 worse in 2 of 9:

| Pair | n | before | after | change |
|---|---:|---:|---:|---:|
| de->de | 159 | 0.934 | 0.934 | +0.000 |
| de->fr | 149 | 0.893 | 0.886 | -0.007 |
| de->it | 147 | 0.939 | 0.945 | +0.007 |
| fr->de | 184 | 0.940 | 0.945 | +0.005 |
| fr->fr | 196 | 0.933 | 0.933 | -0.000 |
| fr->it | 189 | 0.963 | 0.968 | +0.005 |
| it->de | 152 | 0.953 | 0.953 | +0.000 |
| it->fr | 152 | 0.966 | 0.967 | +0.001 |
| it->it | 160 | 0.954 | 0.961 | +0.007 |
