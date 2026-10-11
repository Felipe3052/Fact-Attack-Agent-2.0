## E1_legal_cap2 vs. B0_submission — task A, 1488 cases (1149 unique)

Overrides: `LEGAL_TEXT_MAX_PAGES=2`

| Metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Macro-F1 | 0.943 | 0.937 | -0.005 |
| Macro-F1, de-duplicated | 0.944 | 0.943 | -0.002 |
| Macro-F1, cross-language | 0.943 | 0.939 | -0.005 |
| Evidence Hit@5 | 0.869 | 0.866 | -0.003 |
| Input tokens / case | 3866 | 3752 | -2.9% |
| Output tokens / case | 76 | 77 | +0.5% |
| F1 entailment | 0.933 | 0.930 | -0.004 |
| F1 neutral | 0.958 | 0.954 | -0.005 |
| F1 contradiction | 0.936 | 0.928 | -0.008 |

- Macro-F1 change, 95 % interval (bootstrap over voting dates): [-0.017, +0.005]
- Labels fixed / broken: 11 / 19; evidence fixed / broken: 14 / 17
- Noise floor (baseline run twice, 1488 cases): labels 3 / 0, evidence 4 / 3
- Cases answered through the CLI failure path: 0 / 0

Folds (date-grouped) — macro-F1 worse in 3 of 5:

| Fold | F1 before | F1 after | Change | Hit@5 before | Hit@5 after |
|---|---:|---:|---:|---:|---:|
| A:0 | 0.977 | 0.990 | +0.013 | 0.914 | 0.921 |
| A:1 | 0.932 | 0.907 | -0.026 | 0.868 | 0.837 |
| A:2 | 0.966 | 0.960 | -0.005 | 0.893 | 0.893 |
| A:3 | 0.919 | 0.897 | -0.022 | 0.852 | 0.858 |
| A:4 | 0.919 | 0.932 | +0.013 | 0.819 | 0.824 |

Language pairs (source→claim) — macro-F1 worse in 4 of 9:

| Pair | n | before | after | change |
|---|---:|---:|---:|---:|
| de->de | 159 | 0.934 | 0.947 | +0.013 |
| de->fr | 149 | 0.893 | 0.893 | +0.000 |
| de->it | 147 | 0.939 | 0.924 | -0.015 |
| fr->de | 184 | 0.940 | 0.940 | +0.000 |
| fr->fr | 196 | 0.933 | 0.908 | -0.026 |
| fr->it | 189 | 0.963 | 0.948 | -0.015 |
| it->de | 152 | 0.953 | 0.953 | +0.000 |
| it->fr | 152 | 0.966 | 0.966 | -0.000 |
| it->it | 160 | 0.954 | 0.954 | +0.000 |
