## HO_E2_reference_6000 vs. HO_baseline — task A, 90 cases (90 unique)

Overrides: `REFERENCE_MAX_CHARS=6000`

| Metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Macro-F1 | 0.933 | 0.944 | +0.011 |
| Macro-F1, de-duplicated | 0.933 | 0.944 | +0.011 |
| Macro-F1, cross-language | 0.899 | 0.916 | +0.017 |
| Evidence Hit@5 | 0.833 | 0.850 | +0.017 |
| Input tokens / case | 3883 | 3863 | -0.5% |
| Output tokens / case | 72 | 67 | -6.6% |
| F1 entailment | 0.967 | 0.967 | +0.000 |
| F1 neutral | 0.923 | 0.938 | +0.014 |
| F1 contradiction | 0.909 | 0.929 | +0.019 |

- Macro-F1 change, 95 % interval (bootstrap over voting dates): [+0.011, +0.011]
- Labels fixed / broken: 1 / 0; evidence fixed / broken: 1 / 0
- Cases answered through the CLI failure path: 0 / 0

Folds (date-grouped) — macro-F1 worse in 0 of 1:

| Fold | F1 before | F1 after | Change | Hit@5 before | Hit@5 after |
|---|---:|---:|---:|---:|---:|
| A:0 | 0.933 | 0.944 | +0.011 | 0.833 | 0.850 |

Language pairs (source→claim) — macro-F1 worse in 0 of 9:

| Pair | n | before | after | change |
|---|---:|---:|---:|---:|
| de->de | 10 | 1.000 | 1.000 | +0.000 |
| de->fr | 10 | 0.600 | 0.852 | +0.252 |
| de->it | 10 | 0.852 | 0.852 | +0.000 |
| fr->de | 10 | 0.785 | 0.785 | +0.000 |
| fr->fr | 10 | 1.000 | 1.000 | +0.000 |
| fr->it | 10 | 1.000 | 1.000 | +0.000 |
| it->de | 10 | 0.852 | 0.852 | +0.000 |
| it->fr | 10 | 1.000 | 1.000 | +0.000 |
| it->it | 10 | 1.000 | 1.000 | +0.000 |
