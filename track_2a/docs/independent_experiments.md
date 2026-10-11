# Independent experiments — generalisation to unseen voting dates (from 2026-10-11)

Goal: better expected performance on **unseen voting dates, claims and language pairs** under the full
competition score (macro-F1, evidence Hit@5, tokens, non-LLM time), not a higher score on a split we already know.
Every change is our own hypothesis, implemented in our code and judged with our own runs. Results of other teams
serve as inspiration only; no code, prompt or pipeline of another team is used.

## 1. Data status and protocol

- **Population:** OST dataset v1.1 (pinned revision `9ff08597`, 1,488 rows → 1,488 task A + 1,488 task B cases),
  20 voting dates, prepared by `scripts/prepare_competition_cases.py` into 5 folds grouped by voting date (seed 42,
  all languages of a date in one fold).
- **Everything here is development data.** All 20 dates have been used for earlier design decisions; the former
  test split (5 dates, 401/402 pairs) served several before/after decisions and is **not an independent holdout**.
  Grouped folds measure how stable a change is across voting dates; they do not prove generalisation to unseen
  dates.
- **Duplicates:** 575 of 1,495 rows (236 groups) are exact duplicates of (claim, booklet) with identical labels;
  12 claim texts occur at more than one date, 3 in both former splits. Reports therefore add macro-F1 on
  de-duplicated groups and a bootstrap over voting dates rather than over rows.
- **Only near-unseen check:** our 36 claims on the 27 September 2026 booklet (not in the repository). Task A there
  is 0.77–0.80 — a warning sign, not a precise estimate (n = 36, own claims, already looked at for two decisions).
  **The set itself is lost:** it was never committed and is in no branch, remote, earlier scratchpad or user folder
  on this machine (searched 2026-10-11); only the scores in `docs/experiments.md` remain.
- **New untouched holdout (built 2026-10-11):** 90 own claims × task A/B on the booklets of the
  **27 September 2026** vote (Neutralitätsinitiative, Ernährungsinitiative; downloaded from admin.ch, not part of
  the dataset). 30 entailment / 30 neutral / 30 contradiction, 10 claims per source→claim language pair, claim
  types (Federal Council, summary, committee, legal text, consequences of a yes) in roughly the dataset's
  proportions per label. Each claim names its basis page; contradictions change exactly one fact; neutral claims
  concern a topic the booklet does not address. Gold references follow the dataset (vote title + PyMuPDF text of
  the part the claim refers to; the detailed explanation for consequence and neutral claims).
  `data/holdout_2026-09-27/claims.jsonl` (sha256 `66528247…70bf54`) and `manifest.json` freeze it;
  `scripts/build_holdout.py` rebuilds the cases from the official PDFs and checks their hashes.
  **Rules:** written before any system ran on these booklets; never used to choose or tune anything; run
  **once**, at the end, on the final candidate and on the baseline. Limitations: written by the same person/agent
  that develops the changes (an independent label check, e.g. by Josip, is advisable), own claims may differ in
  style from the organisers', two proposals only, n = 90 per task (macro-F1 ± ~0.05).
- **Decision rule:** a change is adopted only if its benefit clears the run-to-run noise of the unchanged system,
  is not concentrated in single folds or language pairs, and costs no relevant quality, evidence or efficiency.

## 2. Reproducibility of the submission configuration (E0)

- The Docker image sets none of the pipeline variables, so the **submission runs on the defaults of
  `src/config.py`**. `.env.example` (repository root and `track_2a/`, kept identical) now lists every setting
  with that default; `tests/test_submission_config.py` checks file and code agree, also inside the image.
- **Local discrepancy found:** the developer `.env` files (not in git, excluded from the image) set
  `NLI_STRATEGY=retrieval` (the old proposal filter) and, in `track_2a/.env`, `LLM_NAME=swiss-ai/Apertus-v1.5-8B`.
  Any local run from `track_2a/` that relied on them measured a different system than the submission
  (one unit test also failed because of it). The image is not affected (`.dockerignore` excludes `.env`).
- **Decision runs** use `scripts/run_decision.py`: it forces the settings of `.env.example` (+ explicit overrides),
  checks the effective configuration, calls the official CLI exactly as the jury does
  (`python -m src --input … --output …`), scores with the vendored official `evaluate.py`, and saves predictions,
  official score, per-fold/language/class metrics, the run manifest (commit, source hashes, settings, CLI timing,
  cases answered through the CLI failure path) and, for uncommitted sources, the exact diff under
  `results/generalization/<run>/`. Before/after reports: `scripts/report_decision.py`.
- Documented final numbers before this work (test 401: A 0.945 / Hit@5 0.839, B 0.975) cannot be checked from the
  repository: their prediction files were never committed.

## 3. Experiments

| ID | Date | Hypothesis | Status |
|---|---|---|---|
| E0 | 2026-10-11 | Baseline of the exact submission configuration on all 2,976 cases | done (reference) |
| E1 | 2026-10-11 | Fewer legal-text pages let the explanation pages into the context (task A) | **rejected** |
| E2 | 2026-10-11 | Task B: a long reference can be cut to its relevant chunks without losing quality | **adopt** (pending holdout) |
| E3 | 2026-10-11 | Task A: tighter page windows (2,000 instead of 3,000 characters) save tokens at equal quality | running |

### E0 — baseline (`results/generalization/B0_submission`)

Commit `3bf73bd`, unchanged sources, submission defaults (then written out in `configs/submission.env`, now in
`.env.example` with the same values), official CLI, 4 workers, booklet parses cached
(as in the image), translations acquired cold. 2,976 cases, 0 failed cases, 0 API failures.

| Task | Macro-F1 | Fold mean ± sd (min–max) | Cross-language F1 | Hit@5 | Input / output tokens per case |
|---|---:|---:|---:|---:|---:|
| A | 0.943 | 0.943 ± 0.024 (0.919–0.977) | 0.943 | 0.869 | 3,866 / 76 |
| B | 0.981 | 0.981 ± 0.004 (0.976–0.985) | 0.979 | – | 2,482 / 56 |

On the 5 dates of the former test split (398 v1.1 pairs) the run gives A 0.942 / Hit@5 0.833 and B 0.972, which
matches the documented 0.945 / 0.839 / 0.975 within run-to-run variation: **the documented numbers reproduce**.
Task A varies across date folds by ±0.024, i.e. a single split can be off by several points. CLI non-LLM time
0.3 ms per case in this mixed, concurrent run (local estimate, not the proxy's measurement).

**Errors of E0** (task A 85, task B 28 of 1,488 each; gold → predicted):

| Task | E→C | E→N | C→N | C→E | N→C | N→E |
|---|---:|---:|---:|---:|---:|---:|
| A | 34 | 20 | 19 | 8 | 3 | 1 |
| B | 5 | 0 | 11 | 6 | 6 | 0 |

- Missing information is rarely read as a contradiction (N→C: 3 in task A); the largest confusion is a supported
  claim read as contradicted (E→C).
- Task A error rate by the part of the booklet a claim names: consequences of a yes ("Wird die Vorlage
  angenommen …") 15.5 % (30/194), committee 7.6 %, legal text 6.3 %, summary 5.0 %, Federal Council 0.2 %.
  The same consequence claims fail in only 3.6 % of task B cases, where the right passage is given: their
  task A errors come mostly from page selection, not from reading — the bottleneck E1 addresses.

**Run-to-run noise** (`results/generalization/B0b_repeat`: the unchanged configuration run a second time, with the
E1/E2 code present but switched off): task A 0.945 / Hit@5 0.870, task B 0.982. Compared with E0 only **3 labels in
task A and 2 in task B** of 1,488 changed (evidence 4 / 3); no fold got worse. The endpoint answers almost
deterministically, so the label changes of an experiment are effects of the change, not noise. It also shows that the
refactoring for E1/E2 does not change the behaviour while their flags are off.

### E1 — page selection in task A: cap the legal-text pages

- **Bottleneck (own analysis, no API):** the gold page is among the 8 selected pages in 0.928 of the
  de-duplicated gold-0/2 cases, but only 0.903 for claims about the summary and 0.761 for claims about the
  consequences of a yes ("Wird die Vorlage angenommen …"); per voting date the recall@8 ranges 0.755–1.000.
  In the misses the gold page sits just below the cut (rank 9–12) while legal-text pages hold ~40 % of the
  top-8 places: the legal text repeats the vote title, which the ranking weights twice.
- **Hypothesis:** at most 2 legal-text pages in the context (the next pages by rank take the freed places, the
  context size stays 8) bring the explanation pages in without hurting claims about the legal text.
- **Own implementation:** `section_caps` in `PassageRetriever.retrieve_hybrid`, switched by
  `LEGAL_TEXT_MAX_PAGES` (default 0 = off). It relies only on our existing legal-text section label, not on how a
  claim is phrased.
- **Offline selection of the variant** (original query only, a lower bound for the production `union` ranking):

  | Variant | recall@8 | worst date @8 | dates better / worse | legal-text claims @8 |
  |---|---:|---:|---:|---:|
  | production | 0.928 | 0.755 | – | 0.984 |
  | **cap 2, every claim** | **0.943** | **0.837** | **8 / 0** | 0.984 |
  | cap 1, every claim | 0.933 | 0.857 | 8 / 6 | 0.855 |
  | cap 1 unless the claim names the legal text | 0.953 | 0.867 | 11 / 0 | 0.984 |

  The cap-1 variant that exempts legal-text claims is better offline but depends on recognising the claim's
  wording; the plain cap of 2 is chosen because it does not, which we expect to transfer better to unseen claims.
  The implementation selects the same pages as the simulation in 402/402 test cases.
- **Nested check of the choice** (does picking a variant on some dates transfer to dates not used for picking?).
  Rule fixed before looking: among variants worse on no selection date, the highest per-date mean recall@8.

  | Variant | select on folds 0–2 → held-out folds 3–4 | select on folds 3–4 → held-out folds 0–2 |
  |---|---:|---:|
  | production | 0.912 | 0.946 |
  | cap 2, every claim (tested in E1) | 0.934 (3 dates better / 0 worse) | 0.957 (5 / 0) |
  | cap 1 unless the claim names the legal text | 0.944 (4 / 0) | 0.966 (7 / 0) |

  The effect holds on the held-out dates in both directions. The rule picks the claim-dependent cap-1 variant both
  times; it stays a candidate (E1b) with the risk that a claim about the legal text which we do not recognise is
  treated like any other claim (cap 1 for every claim drops legal-text claims from 0.984 to 0.855).
- **Related earlier result:** on 2026-10-08 a context filter `low+legal1` (at most one legal-text page, other
  low-value pages dropped, **freed places not refilled**) was rejected: dev 300 macro-F1 0.927 → 0.910, Sep 2026
  set 0.804 → 0.779. E1 differs in refilling the freed places (the context keeps 8 pages) and in allowing two
  legal-text pages; whether that difference matters is exactly what the API run has to show.
- **Result** (`results/generalization/E1_legal_cap2`, `LEGAL_TEXT_MAX_PAGES=2`, task A, 1,488 cases, same CLI
  path, 0 failed cases; full report in `report/report.md`):

  | | Baseline E0 | E1 | Change |
  |---|---:|---:|---:|
  | Macro-F1 | 0.943 | 0.937 | −0.005 (95 % date bootstrap −0.017 … +0.005) |
  | Macro-F1, de-duplicated | 0.944 | 0.943 | −0.002 |
  | Evidence Hit@5 | 0.869 | 0.866 | −0.003 |
  | Input tokens / case | 3,866 | 3,752 | −2.9 % |
  | Folds / language pairs worse | – | 3 of 5 / 4 of 9 | |

  Labels fixed / broken: 11 / 19. By the part a claim names: consequence claims 4 / 1 and summary claims 3 / 6,
  but **legal-text claims 0 / 10** — although their gold page stayed in the context (offline recall unchanged at
  0.984). Questions about the legal text need the other legal-text pages as context, not only the one page that
  holds the gold passage; recall@k of the gold page does not capture that.
- **Decision: rejected.** No gain in macro-F1 or Hit@5, worse in most folds; the token saving (−2.9 %) does not
  make up for it. The 30 changed labels are far above the 3 changes of the repeated baseline: the harm is real. E1b (exempt claims that name the legal text) would avoid the ten breaks, but what remains
  (non-legal-text claims 11 fixed / 9 broken) is within run-to-run noise; not pursued before the deadline.
- **Lesson for the method:** the offline proxy (gold page among the selected pages) overstated the benefit; for
  context changes it must be complemented by an API run before any claim of improvement.
- **Provenance:** the observation that claim openings name the booklet part they refer to was described publicly
  by another team (Voting NLI). It led us to break our recall down by the part a claim names; the bottleneck
  (legal text crowding out explanation pages) and the fix are our own findings and design.

### E2 — task B: relevant chunks of long references

- **Bottleneck (own analysis):** task B sends the whole reference (mean 7,048 characters, ~2,530 input tokens per
  case). All 498 neutral references are longer than 8,000 characters (median 14,568), entailment/contradiction
  references only in 34 of 997 cases. This length pattern is a property of the development data; the method must
  not and does not use length as a signal for the label.
- **Hypothesis:** a reference longer than `REFERENCE_MAX_CHARS` can be sent as its first chunk plus the chunks
  that best match the claim, in document order, without a relevant loss in macro-F1.
- **Own implementation:** `ClaimVerificationEngine._focus_reference`, using our existing reference chunking and
  BM25 ranking; for a claim in another language it adds the claim's translation to the query (our existing
  retrieval translation, its tokens counted). Default 0 = off.
- **Budget chosen up front: 6,000 characters** (mean reference characters sent −42 %; 91 of 997
  entailment/contradiction references would be cut, each only moderately). The choice used the length
  distribution of the development data and is documented as such.
- **Provenance:** another team (Voting NLI) reported publicly that cutting long task-B references saved tokens at
  equal macro-F1. Our variant (chunking, BM25 + translation, opening chunk, character budget) is our own and is
  tested against our full-text baseline on our folds.
- **Result** (`results/generalization/E2_reference_6000`, `REFERENCE_MAX_CHARS=6000`, task B, 1,488 cases,
  0 failed cases; full report in `report/report.md`):

  | | Baseline E0 | E2 | Change |
  |---|---:|---:|---:|
  | Macro-F1 | 0.981 | 0.984 | +0.003 (95 % date bootstrap −0.002 … +0.008) |
  | Macro-F1, de-duplicated | 0.979 | 0.983 | +0.004 |
  | Macro-F1, cross-language | 0.979 | 0.984 | +0.005 |
  | Input / output tokens per case | 2,482 / 56 | 1,732 / 62 | **−30.2 %** / +10 % (translation answers) |
  | Folds / language pairs worse | – | 1 of 5 (−0.007) / 1 of 9 (it→fr −0.014) | |

  589 of 1,488 references were cut; among them, the 91 entailment/contradiction cases are correct 79 times before
  and after (no net loss where information could be cut away). Labels fixed / broken 9 / 4 (unique claims 8 / 3:
  two broken rows are the same claim). All per-class F1 within ±0.007.
- **Decision: adopt**, subject to the one final run on the untouched 27 September 2026 holdout. (a) Noise check
  done: 13 changed labels against 2 for the repeated baseline, so the changes are caused by E2, with a net gain of 5. The token saving is large and
  stable; quality does not drop in any class and in at most one fold / pair by less than the bootstrap width.

## 4. Sources read (reports only, no code)

| Team / repository | Commit read | Date | License | Used for |
|---|---|---|---|---|
| Voting NLI, `Rashad18236/hackapertus-voting-nli` (technical report, README) | `42b2a3c` | 2026-10-11 | Apache-2.0 | inspiration for E1 analysis and E2 |
| Apertus Evidence Lab, `hallzyx/apertus` (technical report, README) | `d28c058` | 2026-10-11 | Apache-2.0 | retrieval as separate bottleneck; trained head not applicable (needs hidden states, our endpoint is chat completions only) |

### E3 — task A: tighter page windows

- **Bottleneck:** task A sends ~3,866 input tokens per case, mostly the 8 selected pages (~11,300 characters after
  the existing 3,000-character window per page); tokens are scored relative to the most frugal team.
- **Hypothesis:** a 2,000-character window per page (the window that best matches claim and vote title, as today)
  keeps the information the model needs while sending fewer tokens. E1 showed that removing whole pages removes
  needed context, so this experiment keeps all 8 pages and only narrows each one. One variable: `PAGE_MAX_CHARS`.
- **Offline estimate (written down before the API run):** context −11 % (≈ −8 % input tokens with the prompt),
  pages narrowed 9.6 % → 23.8 %, share of gold-passage words still visible on gold pages 0.997 → 0.968
  (16 of 734 cases lose more than 20 %). 1,500 characters would save −26 % but lose more than 20 % of the gold
  words in 282 of 734 cases and is not tested. Evidence is built from the full page and is not narrowed.
- **Provenance:** own analysis; no external source.
