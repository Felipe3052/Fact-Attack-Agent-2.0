## HO_E25_s_role vs. HO_E23_legal_text — task A, 90 cases (90 unique)

Overrides: `A_PROMPT_DROP=role`

| Metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Macro-F1 | 0.989 | 0.989 | +0.000 |
| Macro-F1, de-duplicated | 0.989 | 0.989 | +0.000 |
| Macro-F1, cross-language | 0.983 | 0.983 | +0.000 |
| Evidence Hit@5 | 0.983 | 0.983 | +0.000 |
| Input tokens / case | 1825 | 1791 | -1.9% |
| Output tokens / case | 57 | 57 | -0.3% |
| F1 entailment | 1.000 | 1.000 | +0.000 |
| F1 neutral | 0.984 | 0.984 | +0.000 |
| F1 contradiction | 0.983 | 0.983 | +0.000 |

- Macro-F1 change, 95 % interval (bootstrap over voting dates): [+0.000, +0.000]
- Labels fixed / broken: 0 / 0; evidence fixed / broken: 0 / 0
- Cases answered through the CLI failure path: 0 / 0

Folds (date-grouped) — macro-F1 worse in 0 of 1:

| Fold | F1 before | F1 after | Change | Hit@5 before | Hit@5 after |
|---|---:|---:|---:|---:|---:|
| A:0 | 0.989 | 0.989 | +0.000 | 0.983 | 0.983 |

Language pairs (source→claim) — macro-F1 worse in 0 of 9:

| Pair | n | before | after | change |
|---|---:|---:|---:|---:|
| de->de | 10 | 1.000 | 1.000 | +0.000 |
| de->fr | 10 | 1.000 | 1.000 | +0.000 |
| de->it | 10 | 1.000 | 1.000 | +0.000 |
| fr->de | 10 | 1.000 | 1.000 | +0.000 |
| fr->fr | 10 | 1.000 | 1.000 | +0.000 |
| fr->it | 10 | 1.000 | 1.000 | +0.000 |
| it->de | 10 | 1.000 | 1.000 | +0.000 |
| it->fr | 10 | 0.915 | 0.915 | +0.000 |
| it->it | 10 | 1.000 | 1.000 | +0.000 |
