"""E7: paired full task A evaluation (1,488 cases) of A_COMPACT_PROMPT against a fresh baseline, offline.

Inputs: results/generalization/E7_baseline_fresh and E7_compact (run_decision.py outputs), the preflight journal of a
mock dry run (preflight_prompt_inputs.jsonl, hashes only), and the pinned dataset for gold labels/passages (--data,
never committed). Matrices: rows = gold, columns = prediction, order Entailment, Contradiction, Neutral (ids 0, 2, 1).
Hit@5: official matcher; denominator = cases with gold entailment/contradiction; a neutral answer is a miss.
Uncertainty: paired bootstrap over voting dates (whole dates resampled with replacement) and leave-one-date-out.

usage (from track_2a): python results/generalization/E7_analysis/analyze_full_eval.py --data .cache/gen/data
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
GEN = HERE.parent
sys.path.insert(0, str(GEN.parents[1]))
from vendor.hackapertus_starter.evaluate import macro_f1, quote_matches, quotes_of  # noqa: E402

ORDER, NAME = [0, 2, 1], {0: "E", 1: "N", 2: "C"}
RUNS = {"baseline": "E7_baseline_fresh", "compact": "E7_compact"}


def jl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True, help="pinned dataset (scripts/prepare_competition_cases.py)")
    parser.add_argument("--rounds", type=int, default=5000)
    args = parser.parse_args()
    gold_rows = {g["id"]: g for g in jl(args.data / "expected-labels.jsonl") if g["id"].endswith("-A")}
    folds = {f["id"]: f for f in jl(args.data / "folds.jsonl") if f["id"].endswith("-A")}
    gold = {i: g["label"] for i, g in gold_rows.items()}
    pred = {k: {p["id"]: p for p in jl(GEN / r / "predictions.jsonl")} for k, r in RUNS.items()}
    journal = {k: {e["id"]: e for e in jl(GEN / r / "prompt_inputs.jsonl")} for k, r in RUNS.items()}
    pre = {e["id"]: e for e in jl(HERE / "preflight_prompt_inputs.jsonl")}
    ids = sorted(gold)
    assert all(set(pred[k]) == set(ids) for k in pred), "prediction ids differ"
    hit = {k: {i: any(quote_matches(q, gold_rows[i]["reference"], 90, 5000) for q in quotes_of(pred[k][i]))
               for i in ids if gold[i] in (0, 2)} for k in RUNS}
    out = {"input_check": {}, "aggregate": {}, "folds": {}, "paired": {}, "dates": {}, "uncertainty": {}, "runs": {}}

    for k in RUNS:
        out["input_check"][k] = {
            "journal_entries": len(journal[k]),
            "input_sha256_equal_to_preflight": sum(journal[k][i]["input_sha256"] == pre[i]["input_sha256"] for i in ids),
            "compact_prompt_flag": sum(bool(journal[k][i].get("compact_prompt")) for i in ids),
            "other_prompt_flags": sum(bool(journal[k][i].get("relation_prompt")) or bool(journal[k][i].get("skill_prompt")) for i in ids)}

    def stats(k, sel):
        pairs = [(gold[i], pred[k][i]["label"]) for i in sel]
        ev = [i for i in sel if gold[i] in (0, 2)]
        m = [pred[k][i]["metrics"] for i in sel]
        return {"n": len(sel), "macro_f1": round(macro_f1(pairs)[0], 4), "accuracy": round(sum(a == b for a, b in pairs) / len(pairs), 4),
                "errors": sum(a != b for a, b in pairs),
                "confusion_E_C_N": [[sum(1 for a, b in pairs if a == g and b == p) for p in ORDER] for g in ORDER],
                "transitions": dict(sorted(Counter(f"{NAME[a]}->{NAME[b]}" for a, b in pairs if a != b).items())),
                "hit5": f"{sum(hit[k][i] for i in ev)}/{len(ev)}", "hit5_rate": round(sum(hit[k][i] for i in ev) / len(ev), 4),
                "input_tokens_mean": round(sum(x["input_tokens"] for x in m) / len(m), 1),
                "output_tokens_mean": round(sum(x["output_tokens"] for x in m) / len(m), 1)}

    def paired(sel):
        b, c = pred["baseline"], pred["compact"]
        fmt = lambda i: f"{NAME[gold[i]]}: {NAME[b[i]['label']]}->{NAME[c[i]['label']]}"
        fixed = [i for i in sel if b[i]["label"] != gold[i] and c[i]["label"] == gold[i]]
        broken = [i for i in sel if b[i]["label"] == gold[i] and c[i]["label"] != gold[i]]
        moved = [i for i in sel if b[i]["label"] != gold[i] != c[i]["label"] and b[i]["label"] != c[i]["label"]]
        ev = [i for i in sel if gold[i] in (0, 2)]
        return {"labels_changed": sum(b[i]["label"] != c[i]["label"] for i in sel), "fixed": len(fixed), "broken": len(broken),
                "wrong_to_other_wrong": len(moved), "fixed_by": dict(Counter(map(fmt, fixed))),
                "broken_by": dict(Counter(map(fmt, broken))), "moved_by": dict(Counter(map(fmt, moved))),
                "hit5_gained": sum(hit["compact"][i] and not hit["baseline"][i] for i in ev),
                "hit5_lost": sum(hit["baseline"][i] and not hit["compact"][i] for i in ev)}

    for k in RUNS:
        out["aggregate"][k] = stats(k, ids)
    out["paired"]["all"] = paired(ids)
    for f in sorted({folds[i]["fold"] for i in ids}):
        sel = [i for i in ids if folds[i]["fold"] == f]
        out["folds"][str(f)] = {"dates": sorted({folds[i]["date"] for i in sel}), **{k: stats(k, sel) for k in RUNS}, "paired": paired(sel)}
    by_date = defaultdict(list)
    for i in ids:
        by_date[folds[i]["date"]].append(i)
    for d, sel in sorted(by_date.items()):
        p = paired(sel)
        out["dates"][d] = {"n": len(sel), "fold": folds[sel[0]]["fold"], "fixed": p["fixed"], "broken": p["broken"],
                           "net": p["fixed"] - p["broken"], "moved": p["wrong_to_other_wrong"],
                           "hit5_net": p["hit5_gained"] - p["hit5_lost"],
                           "macro_f1": {k: stats(k, sel)["macro_f1"] for k in RUNS}}

    # paired uncertainty at voting-date level
    dates = sorted(by_date)

    def deltas(sample_dates):
        sel = [i for d in sample_dates for i in by_date[d]]
        ev = [i for i in sel if gold[i] in (0, 2)]
        f = {k: macro_f1([(gold[i], pred[k][i]["label"]) for i in sel])[0] for k in RUNS}
        h = {k: sum(hit[k][i] for i in ev) / len(ev) for k in RUNS}
        e = {k: sum(pred[k][i]["label"] != gold[i] for i in sel) for k in RUNS}
        return f["compact"] - f["baseline"], h["compact"] - h["baseline"], e["compact"] - e["baseline"]

    rng = random.Random(20261012)
    boot = [deltas([rng.choice(dates) for _ in dates]) for _ in range(args.rounds)]
    q = lambda xs, a: sorted(xs)[int(a * (len(xs) - 1))]
    obs = deltas(dates)
    lodo = {d: deltas([x for x in dates if x != d]) for d in dates}
    nets = [v["net"] for v in out["dates"].values()]
    out["uncertainty"] = {
        "observed": {"delta_macro_f1": round(obs[0], 4), "delta_hit5": round(obs[1], 4), "delta_errors": obs[2]},
        "bootstrap_dates": {"rounds": args.rounds, "seed": 20261012, "dates": len(dates),
                            "delta_macro_f1_95": [round(q([b[0] for b in boot], .025), 4), round(q([b[0] for b in boot], .975), 4)],
                            "delta_hit5_95": [round(q([b[1] for b in boot], .025), 4), round(q([b[1] for b in boot], .975), 4)],
                            "share_delta_f1_le_0": round(sum(b[0] <= 0 for b in boot) / len(boot), 4),
                            "share_delta_hit5_le_0": round(sum(b[1] <= 0 for b in boot) / len(boot), 4)},
        "leave_one_date_out_delta_f1": {"min": round(min(v[0] for v in lodo.values()), 4), "max": round(max(v[0] for v in lodo.values()), 4),
                                        "date_with_min": min(lodo, key=lambda d: lodo[d][0])},
        "dates_net_better_worse_equal": [sum(n > 0 for n in nets), sum(n < 0 for n in nets), sum(n == 0 for n in nets)],
        "largest_single_date_share_of_net_fixes": None}
    total_net = out["paired"]["all"]["fixed"] - out["paired"]["all"]["broken"]
    if total_net > 0:
        out["uncertainty"]["largest_single_date_share_of_net_fixes"] = round(max(nets) / total_net, 3)

    for k, r in RUNS.items():
        run = json.loads((GEN / r / "run.json").read_text(encoding="utf-8"))
        m = [p["metrics"] for p in pred[k].values()]
        score = json.loads((GEN / r / "score.official.json").read_text(encoding="utf-8"))["tasks"]["A"]
        out["runs"][k] = {"run": r, "commit": run.get("commit", "")[:7], "src_uncommitted_changes": run.get("src_uncommitted_changes"),
                          "overrides": run.get("overrides"), "query_cache_dir_name": Path(run.get("query_cache_dir", "")).name,
                          "official_macro_f1": round(score["macro_f1"], 4), "official_evidence": score["evidence"],
                          "official_evidence_score": round(score["evidence_score"], 4),
                          "input_tokens_mean": round(sum(x["input_tokens"] for x in m) / len(m), 1),
                          "output_tokens_mean": round(sum(x["output_tokens"] for x in m) / len(m), 1),
                          "inference_ms_mean": round(sum(x["inference_time_ms"] for x in m) / len(m)),
                          "cli_timing": run.get("cli_timing"), "wall_seconds_outside": run.get("wall_seconds_outside"),
                          "api_failures_logged": run.get("api_failures_logged"), "cases_failed_in_cli": run.get("cases_failed_in_cli")}

    # score scenarios (not an official score): S_A = 0.5 F1 + 0.2 Hit@5 + 0.15 time + 0.15 tokens; total = 0.6 S_A + 0.4 S_B
    r_tok = out["runs"]["compact"]["input_tokens_mean"] / out["runs"]["baseline"]["input_tokens_mean"] - 1
    d_f1, d_hit = out["uncertainty"]["observed"]["delta_macro_f1"], out["uncertainty"]["observed"]["delta_hit5"]
    out["scenarios"] = {"assumptions": "token score = best/own (input+output tokens per case of task A); time score unchanged; "
                                       "T = current task A token score of our submission (unknown, depends on other teams)",
                        "relative_token_increase": round(r_tok, 4),
                        "rows": [{"T": t, "dS_A": round(0.5 * d_f1 + 0.2 * d_hit + 0.15 * t * (1 / (1 + r_tok) - 1), 5),
                                  "dTotal": round(0.6 * (0.5 * d_f1 + 0.2 * d_hit + 0.15 * t * (1 / (1 + r_tok) - 1)), 5)}
                                 for t in (0.25, 0.5, 0.75, 1.0)]}
    (HERE / "full_eval_analysis.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(out["input_check"]))
    for k, r in out["runs"].items():
        print(k, {x: r[x] for x in ("official_macro_f1", "official_evidence", "input_tokens_mean", "output_tokens_mean", "inference_ms_mean",
                                     "cli_timing", "wall_seconds_outside", "api_failures_logged")}, "failed:", len(r["cases_failed_in_cli"] or []))
    for k, s in out["aggregate"].items():
        print(f"GESAMT {k:9s} F1 {s['macro_f1']:.4f} Acc {s['accuracy']:.4f} Fehler {s['errors']} CM(E,C,N) {s['confusion_E_C_N']} Hit@5 {s['hit5']} {s['transitions']}")
    p = out["paired"]["all"]
    print(f"GEPAART korrigiert {p['fixed']} neu falsch {p['broken']} verschoben {p['wrong_to_other_wrong']} Hit +{p['hit5_gained']}/-{p['hit5_lost']}")
    print("  korrigiert:", p["fixed_by"]); print("  neu falsch:", p["broken_by"]); print("  verschoben:", p["moved_by"])
    for f, d in out["folds"].items():
        print(f"FOLD {f} ({len(d['dates'])} Termine, n={d['baseline']['n']}): F1 {d['baseline']['macro_f1']:.4f} -> {d['compact']['macro_f1']:.4f} | "
              f"Acc {d['baseline']['accuracy']:.4f} -> {d['compact']['accuracy']:.4f} | Hit@5 {d['baseline']['hit5']} -> {d['compact']['hit5']} | "
              f"korr {d['paired']['fixed']} neu {d['paired']['broken']} | E->C {d['baseline']['transitions'].get('E->C', 0)}->{d['compact']['transitions'].get('E->C', 0)} "
              f"E->N {d['baseline']['transitions'].get('E->N', 0)}->{d['compact']['transitions'].get('E->N', 0)} N->C {d['baseline']['transitions'].get('N->C', 0)}->{d['compact']['transitions'].get('N->C', 0)}")
    print("TERMINE (Datum: netto korrigiert-neu, Hit netto):", {d: (v["net"], v["hit5_net"]) for d, v in out["dates"].items()})
    print("UNSICHERHEIT:", json.dumps(out["uncertainty"]))
    print("SZENARIEN:", json.dumps(out["scenarios"]))


if __name__ == "__main__":
    main()
