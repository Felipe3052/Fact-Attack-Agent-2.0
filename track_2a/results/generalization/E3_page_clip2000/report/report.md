## E3_page_clip2000 vs. B0_submission — task A, 1488 cases (1149 unique)

Overrides: `PAGE_MAX_CHARS=2000`

| Metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Macro-F1 | 0.943 | 0.934 | -0.008 |
| Macro-F1, de-duplicated | 0.944 | 0.937 | -0.007 |
| Macro-F1, cross-language | 0.943 | 0.933 | -0.010 |
| Evidence Hit@5 | 0.869 | 0.864 | -0.005 |
| Input tokens / case | 3866 | 3514 | -9.1% |
| Output tokens / case | 76 | 77 | +0.9% |
| F1 entailment | 0.933 | 0.928 | -0.005 |
| F1 neutral | 0.958 | 0.947 | -0.011 |
| F1 contradiction | 0.936 | 0.928 | -0.008 |

- Macro-F1 change, 95 % interval (bootstrap over voting dates): [-0.014, -0.002]
- Labels fixed / broken: 6 / 18; evidence fixed / broken: 18 / 23
- Noise floor (baseline run twice, 1488 cases): labels 3 / 0, evidence 4 / 3
- Cases answered through the CLI failure path: 0 / 0

Folds (date-grouped) — macro-F1 worse in 3 of 5:

| Fold | F1 before | F1 after | Change | Hit@5 before | Hit@5 after |
|---|---:|---:|---:|---:|---:|
| A:0 | 0.977 | 0.962 | -0.015 | 0.914 | 0.914 |
| A:1 | 0.932 | 0.933 | +0.000 | 0.868 | 0.874 |
| A:2 | 0.966 | 0.946 | -0.019 | 0.893 | 0.881 |
| A:3 | 0.919 | 0.915 | -0.004 | 0.852 | 0.836 |
| A:4 | 0.919 | 0.919 | +0.000 | 0.819 | 0.819 |

Language pairs (source→claim) — macro-F1 worse in 5 of 9:

| Pair | n | before | after | change |
|---|---:|---:|---:|---:|
| de->de | 159 | 0.934 | 0.913 | -0.020 |
| de->fr | 149 | 0.893 | 0.880 | -0.013 |
| de->it | 147 | 0.939 | 0.918 | -0.021 |
| fr->de | 184 | 0.940 | 0.929 | -0.011 |
| fr->fr | 196 | 0.933 | 0.934 | +0.000 |
| fr->it | 189 | 0.963 | 0.963 | +0.000 |
| it->de | 152 | 0.953 | 0.931 | -0.022 |
| it->fr | 152 | 0.966 | 0.967 | +0.001 |
| it->it | 160 | 0.954 | 0.961 | +0.007 |
