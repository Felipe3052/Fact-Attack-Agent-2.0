## HO_E23_legal_text vs. HO_E12_part_context — task A, 90 cases (90 unique)

Overrides: `none`

| Metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Macro-F1 | 0.956 | 0.989 | +0.033 |
| Macro-F1, de-duplicated | 0.956 | 0.989 | +0.033 |
| Macro-F1, cross-language | 0.967 | 0.983 | +0.016 |
| Evidence Hit@5 | 0.933 | 0.983 | +0.050 |
| Input tokens / case | 1751 | 1825 | +4.2% |
| Output tokens / case | 57 | 57 | +0.2% |
| F1 entailment | 0.983 | 1.000 | +0.017 |
| F1 neutral | 0.938 | 0.984 | +0.046 |
| F1 contradiction | 0.947 | 0.983 | +0.036 |

- Macro-F1 change, 95 % interval (bootstrap over voting dates): [+0.033, +0.033]
- Labels fixed / broken: 3 / 0; evidence fixed / broken: 3 / 0
- Cases answered through the CLI failure path: 0 / 0

Folds (date-grouped) — macro-F1 worse in 0 of 1:

| Fold | F1 before | F1 after | Change | Hit@5 before | Hit@5 after |
|---|---:|---:|---:|---:|---:|
| A:0 | 0.956 | 0.989 | +0.033 | 0.933 | 0.983 |

Language pairs (source→claim) — macro-F1 worse in 0 of 9:

| Pair | n | before | after | change |
|---|---:|---:|---:|---:|
| de->de | 10 | 0.852 | 1.000 | +0.148 |
| de->fr | 10 | 0.915 | 1.000 | +0.085 |
| de->it | 10 | 1.000 | 1.000 | +0.000 |
| fr->de | 10 | 1.000 | 1.000 | +0.000 |
| fr->fr | 10 | 1.000 | 1.000 | +0.000 |
| fr->it | 10 | 1.000 | 1.000 | +0.000 |
| it->de | 10 | 1.000 | 1.000 | +0.000 |
| it->fr | 10 | 0.915 | 0.915 | +0.000 |
| it->it | 10 | 0.915 | 1.000 | +0.085 |
