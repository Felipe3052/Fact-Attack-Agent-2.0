"""Before/after report of a decision run against the baseline, on the cases both runs share (one task or both).

Besides the official metrics it reports what a decision on unseen voting dates needs:
- per date-grouped fold and language pair: the change, and how many groups get worse;
- macro-F1 on de-duplicated (claim, source) groups (38 % of the dataset rows are exact duplicates);
- paired label / evidence changes, and, given a repeated baseline run, the run-to-run flips of an unchanged system
  (the noise floor any change has to clear);
- a 95 % interval of the macro-F1 change from a bootstrap over voting dates (whole dates are resampled).

Usage: python scripts/report_decision.py --data .cache/gen/data --baseline results/generalization/B0_submission
           --candidate results/generalization/E1_... [--repeat results/generalization/B0b_...] --task A
"""

import argparse
import json
from pathlib import Path
import random
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from compare_competition_runs import load, paired_changes, summarize  # noqa: E402
from src.official_evaluation import label_of, macro_f1  # noqa: E402


def task_ids(cases, task):
    return {cid for cid, c in cases.items() if task == "all" or ("booklet" in c) == (task == "A")}


def dedup_ids(ids, cases):
    """One case per (normalised claim, source) group."""
    seen, keep = set(), []
    for cid in sorted(ids):
        c = cases[cid]
        source = c["booklet"]["path"] if "booklet" in c else c["reference"]["text"]
        key = (re.sub(r"\W+", " ", c["claim"]["text"].lower()).strip(), source)
        if key not in seen:
            seen.add(key)
            keep.append(cid)
    return keep


def f1(ids, predictions, gold):
    return macro_f1([(gold[cid]["label"], label_of(predictions[cid])[0]) for cid in ids])[0]


def date_bootstrap(ids, base, cand, gold, folds, rounds=1000, seed=7):
    by_date = {}
    for cid in ids:
        by_date.setdefault(folds[cid]["date"], []).append(cid)
    dates, rng, deltas = sorted(by_date), random.Random(seed), []
    for _ in range(rounds):
        sample = [cid for d in (rng.choice(dates) for _ in dates) for cid in by_date[d]]
        deltas.append(f1(sample, cand, gold) - f1(sample, base, gold))
    deltas.sort()
    return deltas[int(0.025 * rounds)], deltas[int(0.975 * rounds) - 1]


def mean_metric(predictions, ids, key):
    return statistics.mean(predictions[cid].get("metrics", {}).get(key, 0) for cid in ids)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--repeat", type=Path, help="a second run of the unchanged baseline (noise floor)")
    parser.add_argument("--task", choices=["A", "B"], required=True)
    parser.add_argument("--output", type=Path, help="write the report (Markdown) and JSON here")
    args = parser.parse_args()

    cases = load(args.data / "cases.jsonl")
    gold_all = load(args.data / "expected-labels.jsonl")
    folds_all = load(args.data / "folds.jsonl")
    base_all, cand_all = load(args.baseline / "predictions.jsonl"), load(args.candidate / "predictions.jsonl")
    ids = sorted(task_ids(cases, args.task) & set(base_all) & set(cand_all))
    if not ids:
        raise SystemExit("no shared cases")
    pick = lambda d: {cid: d[cid] for cid in ids}  # noqa: E731
    cases_t, gold, folds, base, cand = pick(cases), pick(gold_all), pick(folds_all), pick(base_all), pick(cand_all)
    s_base, s_cand = summarize(base, cases_t, gold, folds), summarize(cand, cases_t, gold, folds)
    t = args.task
    changes = paired_changes(base, cand, gold, cases_t, s_base["case_evidence_hit5"], s_cand["case_evidence_hit5"])
    unique = dedup_ids(ids, cases_t)
    low, high = date_bootstrap(ids, base, cand, gold, folds)
    run_info = {name: json.loads((path / "run.json").read_text(encoding="utf-8"))
                for name, path in (("baseline", args.baseline), ("candidate", args.candidate))}

    report = {"task": t, "cases": len(ids), "unique_groups": len(unique),
              "baseline": str(args.baseline.name), "candidate": str(args.candidate.name),
              "candidate_overrides": run_info["candidate"].get("overrides"),
              "macro_f1": [s_base["tasks"][t]["macro_f1"], s_cand["tasks"][t]["macro_f1"]],
              "macro_f1_dedup": [f1(unique, base, gold), f1(unique, cand, gold)],
              "macro_f1_change_95ci_date_bootstrap": [low, high],
              "cross_language_macro_f1": [s_base["tasks"][t]["cross_language_macro_f1"],
                                          s_cand["tasks"][t]["cross_language_macro_f1"]],
              "evidence_hit5": [s_base["tasks"][t]["evidence_hit5"], s_cand["tasks"][t]["evidence_hit5"]],
              "per_class_f1": {label: [s_base["tasks"][t]["per_class"][label]["f1"], s_cand["tasks"][t]["per_class"][label]["f1"]]
                               for label in s_base["tasks"][t]["per_class"]},
              "folds": {k: [s_base["folds"][k]["macro_f1"], s_cand["folds"][k]["macro_f1"],
                            s_base["folds"][k]["evidence_hit5"], s_cand["folds"][k]["evidence_hit5"]]
                        for k in sorted(s_base["folds"])},
              "language_pairs": {k: [s_base["by_language"][k]["macro_f1"], s_cand["by_language"][k]["macro_f1"],
                                     s_base["by_language"][k]["cases"]] for k in sorted(s_base["by_language"])},
              "labels_fixed_broken": [len(changes["fixed"]), len(changes["broken"])],
              "evidence_fixed_broken": [len(changes["evidence_fixed"]), len(changes["evidence_broken"])],
              "fixed_ids": changes["fixed"], "broken_ids": changes["broken"],
              "input_tokens_mean": [mean_metric(base, ids, "input_tokens"), mean_metric(cand, ids, "input_tokens")],
              "output_tokens_mean": [mean_metric(base, ids, "output_tokens"), mean_metric(cand, ids, "output_tokens")],
              "cli_failed_cases": [len(run_info["baseline"].get("cases_failed_in_cli", [])),
                                   len(run_info["candidate"].get("cases_failed_in_cli", []))],
              "cli_non_llm_ms_per_case_mixed_run": [(run_info[n].get("cli_timing") or {}).get("non_llm_ms_per_case")
                                                    for n in ("baseline", "candidate")]}
    if args.repeat:
        rep = {cid: v for cid, v in load(args.repeat / "predictions.jsonl").items() if cid in gold}
        shared = [cid for cid in ids if cid in rep]
        noise = paired_changes({c: base[c] for c in shared}, {c: rep[c] for c in shared}, {c: gold[c] for c in shared},
                               {c: cases_t[c] for c in shared})
        report["noise_floor_repeat_baseline"] = {
            "cases": len(shared), "labels_fixed_broken": [len(noise["fixed"]), len(noise["broken"])],
            "evidence_fixed_broken": [len(noise["evidence_fixed"]), len(noise["evidence_broken"])],
            "macro_f1": f1(shared, rep, gold)}

    fmt = lambda v: "–" if v is None else f"{v:.3f}"  # noqa: E731
    d = lambda pair: "–" if None in pair[:2] else f"{pair[1] - pair[0]:+.3f}"  # noqa: E731
    fold_rows = report["folds"].items()
    lines = [f"## {report['candidate']} vs. {report['baseline']} — task {t}, {len(ids)} cases ({len(unique)} unique)", "",
             f"Overrides: `{' '.join(report['candidate_overrides'] or []) or 'none'}`", "",
             "| Metric | Baseline | Candidate | Change |", "|---|---:|---:|---:|"]
    for name, key in (("Macro-F1", "macro_f1"), ("Macro-F1, de-duplicated", "macro_f1_dedup"),
                      ("Macro-F1, cross-language", "cross_language_macro_f1"), ("Evidence Hit@5", "evidence_hit5"),
                      ("Input tokens / case", "input_tokens_mean"), ("Output tokens / case", "output_tokens_mean")):
        a, b = report[key]
        lines.append(f"| {name} | {fmt(a) if 'tokens' not in key else f'{a:.0f}'} | "
                     f"{fmt(b) if 'tokens' not in key else f'{b:.0f}'} | "
                     f"{d(report[key]) if 'tokens' not in key else f'{(b - a) / a:+.1%}'} |")
    for label, pair in report["per_class_f1"].items():
        lines.append(f"| F1 {label} | {fmt(pair[0])} | {fmt(pair[1])} | {d(pair)} |")
    lines += ["", f"- Macro-F1 change, 95 % interval (bootstrap over voting dates): [{low:+.3f}, {high:+.3f}]",
              f"- Labels fixed / broken: {report['labels_fixed_broken'][0]} / {report['labels_fixed_broken'][1]}"
              + (f"; evidence fixed / broken: {report['evidence_fixed_broken'][0]} / {report['evidence_fixed_broken'][1]}"
                 if t == "A" else "")]
    if "noise_floor_repeat_baseline" in report:
        n = report["noise_floor_repeat_baseline"]
        lines.append(f"- Noise floor (baseline run twice, {n['cases']} cases): labels {n['labels_fixed_broken'][0]} / "
                     f"{n['labels_fixed_broken'][1]}" + (f", evidence {n['evidence_fixed_broken'][0]} / "
                                                          f"{n['evidence_fixed_broken'][1]}" if t == "A" else ""))
    lines.append(f"- Cases answered through the CLI failure path: {report['cli_failed_cases'][0]} / {report['cli_failed_cases'][1]}")
    worse = sum(v[1] < v[0] for _, v in fold_rows)
    lines += ["", f"Folds (date-grouped) — macro-F1 worse in {worse} of {len(report['folds'])}:", "",
              "| Fold | F1 before | F1 after | Change" + (" | Hit@5 before | Hit@5 after |" if t == "A" else " |"),
              "|---|---:|---:|---:" + ("|---:|---:|" if t == "A" else "|")]
    for k, v in fold_rows:
        lines.append(f"| {k} | {fmt(v[0])} | {fmt(v[1])} | {d(v)}" + (f" | {fmt(v[2])} | {fmt(v[3])} |" if t == "A" else " |"))
    pairs = report["language_pairs"]
    lines += ["", f"Language pairs (source→claim) — macro-F1 worse in {sum(v[1] < v[0] for v in pairs.values())} of {len(pairs)}:",
              "", "| Pair | n | before | after | change |", "|---|---:|---:|---:|---:|"]
    for k, v in pairs.items():
        lines.append(f"| {k.split(':', 1)[1]} | {v[2]} | {fmt(v[0])} | {fmt(v[1])} | {d(v)} |")
    text = "\n".join(lines) + "\n"
    print(text)
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "report.md").write_text(text, encoding="utf-8")
        (args.output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
