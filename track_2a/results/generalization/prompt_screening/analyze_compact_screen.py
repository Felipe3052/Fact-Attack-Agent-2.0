"""Paired evaluation of the compact-prompt screen (offline): compact vs. fresh baseline (baseline_repeat), with the
stored baseline (noise) and the longer skill as references. Panels are reported separately; the 60 diagnostic cases are
an error analysis, not an estimate.

Matrices: rows = gold, columns = prediction, order Entailment, Contradiction, Neutral (label ids 0, 2, 1).
Hit@5 (official matcher): denominator = cases with gold entailment/contradiction in the panel; a neutral answer is a miss.
usage (from track_2a, after restore_inputs.py): python results/generalization/prompt_screening/analyze_compact_screen.py
"""
import csv
import json
from collections import Counter
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from vendor.hackapertus_starter.evaluate import macro_f1, quote_matches, quotes_of  # noqa: E402

if not (HERE / "input/expected-labels.jsonl").exists():
    raise SystemExit("input/expected-labels.jsonl is not committed: run restore_inputs.py --data <pinned dataset> first")
RUNS = ["baseline", "baseline_repeat", "compact", "skill"]
ORDER, NAME = [0, 2, 1], {0: "E", 1: "N", 2: "C"}


def jl(path):
    return [json.loads(x) for x in open(path, encoding="utf-8") if x.strip()]


sel = {r["id"]: r for r in csv.DictReader(open(HERE / "input/selection.csv", encoding="utf-8"))}
gold_rows = {g["id"]: g for g in jl(HERE / "input/expected-labels.jsonl")}
gold = {i: g["label"] for i, g in gold_rows.items()}
pred = {n: {p["id"]: p for p in jl(HERE / f"runs/{n}/predictions.jsonl")} for n in RUNS}
inputs = {n: {e["id"]: e for e in jl(HERE / f"runs/{n}/prompt_inputs.jsonl")} for n in RUNS}
hit = {n: {i: any(quote_matches(q, gold_rows[i]["reference"], 90, 5000) for q in quotes_of(pred[n][i]))
           for i in sel if gold[i] in (0, 2)} for n in RUNS}
out = {"input_check": {}, "panels": {}, "runs": {}}

for n in RUNS:
    out["input_check"][n] = {
        "cases": len(pred[n]),
        "input_sha256_equal_to_baseline_repeat": sum(inputs[n][i]["input_sha256"] == inputs["baseline_repeat"][i]["input_sha256"] for i in sel),
        "prompt_flags": {k: sum(bool(e.get(k)) for e in inputs[n].values()) for k in ("relation_prompt", "skill_prompt", "compact_prompt")}}


def stats(n, ids):
    pairs = [(gold[i], pred[n][i]["label"]) for i in ids]
    ev = [i for i in ids if gold[i] in (0, 2)]
    return {"macro_f1": round(macro_f1(pairs)[0], 4), "accuracy": round(sum(g == p for g, p in pairs) / len(pairs), 4),
            "errors": sum(g != p for g, p in pairs),
            "confusion_E_C_N": [[sum(1 for g, p in pairs if g == a and p == b) for b in ORDER] for a in ORDER],
            "transitions": dict(sorted(Counter(f"{NAME[g]}->{NAME[p]}" for g, p in pairs if g != p).items())),
            "hit5": f"{sum(hit[n][i] for i in ev)}/{len(ev)}", "hit5_rate": round(sum(hit[n][i] for i in ev) / len(ev), 4),
            "gold_EC_predicted_neutral": sum(pred[n][i]["label"] == 1 for i in ev)}


def paired(base, cand, ids):
    b, c = pred[base], pred[cand]
    fmt = lambda i: f"{NAME[gold[i]]}: {NAME[b[i]['label']]}->{NAME[c[i]['label']]}"
    fixed = [i for i in ids if b[i]["label"] != gold[i] and c[i]["label"] == gold[i]]
    broken = [i for i in ids if b[i]["label"] == gold[i] and c[i]["label"] != gold[i]]
    moved = [i for i in ids if b[i]["label"] != gold[i] != c[i]["label"] and b[i]["label"] != c[i]["label"]]
    ev = [i for i in ids if gold[i] in (0, 2)]
    return {"labels_changed": sum(b[i]["label"] != c[i]["label"] for i in ids), "fixed": len(fixed), "broken": len(broken),
            "wrong_to_other_wrong": len(moved), "fixed_by": dict(Counter(map(fmt, fixed))),
            "broken_by": dict(Counter(map(fmt, broken))), "moved_by": dict(Counter(map(fmt, moved))),
            "hit5_gained": sum(hit[cand][i] and not hit[base][i] for i in ev),
            "hit5_lost": sum(hit[base][i] and not hit[cand][i] for i in ev),
            "fixed_ids": fixed, "broken_ids": broken, "moved_ids": moved}


for panel in ("representative", "baseline_error_diagnostic"):
    ids = sorted(i for i in sel if sel[i]["panel"] == panel)
    out["panels"][panel] = {
        "n": len(ids), "n_gold_EC": sum(gold[i] in (0, 2) for i in ids),
        "runs": {n: stats(n, ids) for n in RUNS},
        "noise_baseline_vs_repeat": paired("baseline", "baseline_repeat", ids),
        "compact_vs_repeat": paired("baseline_repeat", "compact", ids),
        "skill_vs_repeat": paired("baseline_repeat", "skill", ids),
        "compact_vs_skill": paired("skill", "compact", ids),
        "errors_by_claim_type": {n: dict(sorted(Counter(sel[i]["claim_type"] for i in ids if pred[n][i]["label"] != gold[i]).items()))
                                 for n in RUNS}}
out["panels"]["all_180_descriptive"] = {"n": len(sel), "runs": {n: stats(n, sorted(sel)) for n in RUNS}}

for n in RUNS:
    m = [p["metrics"] for p in pred[n].values()]
    run = json.load(open(HERE / f"runs/{n}/run.json", encoding="utf-8"))
    out["runs"][n] = {"input_tokens_mean": round(sum(x["input_tokens"] for x in m) / len(m), 1),
                      "output_tokens_mean": round(sum(x["output_tokens"] for x in m) / len(m), 1),
                      "inference_ms_mean": round(sum(x["inference_time_ms"] for x in m) / len(m)),
                      "cli_timing": run.get("cli_timing"), "api_failures_logged": run.get("api_failures_logged"),
                      "cases_failed_in_cli": run.get("cases_failed_in_cli"), "overrides": run.get("overrides"),
                      "commit": run.get("commit", "")[:7], "src_uncommitted_changes": run.get("src_uncommitted_changes")}

(HERE / "compact_screen_analysis.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(out["input_check"], ensure_ascii=False))
for n, r in out["runs"].items():
    print(f"{n:16s} in {r['input_tokens_mean']:7.1f} out {r['output_tokens_mean']:5.1f} inf {r['inference_ms_mean']} ms "
          f"cli {r['cli_timing']} api_fail {r['api_failures_logged']} failed {len(r['cases_failed_in_cli'] or [])} commit {r['commit']}")
for panel, d in out["panels"].items():
    print(f"\n=== {panel} (n={d['n']}{', gold E/C ' + str(d['n_gold_EC']) if 'n_gold_EC' in d else ''})")
    for n, s in d["runs"].items():
        print(f"  {n:16s} F1 {s['macro_f1']:.4f} Acc {s['accuracy']:.4f} Fehler {s['errors']:2d} CM(E,C,N) {s['confusion_E_C_N']} "
              f"Hit@5 {s['hit5']} (N bei Gold E/C: {s['gold_EC_predicted_neutral']}) {s['transitions']}")
    for key in ("noise_baseline_vs_repeat", "compact_vs_repeat", "skill_vs_repeat", "compact_vs_skill"):
        if key in d:
            p = d[key]
            print(f"  {key:25s} geändert {p['labels_changed']:2d} korr. {p['fixed']} neu {p['broken']} versch. {p['wrong_to_other_wrong']} "
                  f"Hit +{p['hit5_gained']}/-{p['hit5_lost']} | korr. {p['fixed_by']} | neu {p['broken_by']} | versch. {p['moved_by']}")
    if "errors_by_claim_type" in d:
        print("  Fehler nach Claim-Typ:", d["errors_by_claim_type"])
