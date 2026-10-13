"""Paired evaluation of the skill screen (offline): stored baseline, fresh baseline repeat, skill (relation prompt shown
for reference). Panels are reported separately; the 60 diagnostic cases are an error analysis, not an estimate.

Matrices: rows = gold, columns = prediction, both in the order Entailment, Contradiction, Neutral (label ids 0, 2, 1).
usage (from track_2a, after restore_inputs.py): python results/generalization/prompt_screening/analyze_skill_screen.py
"""
import csv
import json
from collections import Counter
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from vendor.hackapertus_starter.evaluate import macro_f1  # noqa: E402

RUNS = ["baseline", "baseline_repeat", "skill", "relation_prompt"]
ORDER, NAME = [0, 2, 1], {0: "E", 1: "N", 2: "C"}


def jl(path):
    return [json.loads(x) for x in open(path, encoding="utf-8") if x.strip()]


if not (HERE / "input/expected-labels.jsonl").exists():
    raise SystemExit("input/expected-labels.jsonl is not committed: run restore_inputs.py --data <pinned dataset> first")
sel = {r["id"]: r for r in csv.DictReader(open(HERE / "input/selection.csv", encoding="utf-8"))}
gold = {g["id"]: g["label"] for g in jl(HERE / "input/expected-labels.jsonl")}
pred = {n: {p["id"]: p for p in jl(HERE / f"runs/{n}/predictions.jsonl")} for n in RUNS}
inputs = {n: {e["id"]: e for e in jl(HERE / f"runs/{n}/prompt_inputs.jsonl")} for n in RUNS}
out = {"input_check": {}, "panels": {}, "runs": {}}

# 1. identical inputs (claim + passages hash of the NLI request) in every run
ref = inputs["baseline"]
for n in RUNS:
    same = sum(inputs[n][i]["input_sha256"] == ref[i]["input_sha256"] for i in sel)
    flags = Counter((e.get("relation_prompt", False), e.get("skill_prompt", False)) for e in inputs[n].values())
    out["input_check"][n] = {"cases": len(pred[n]), "journal_entries": len(inputs[n]), "input_sha256_equal_to_baseline": same,
                             "prompt_flags(relation, skill)": {str(k): v for k, v in flags.items()}}


def stats(n, ids):
    pairs = [(gold[i], pred[n][i]["label"]) for i in ids]
    cm = [[sum(1 for g, p in pairs if g == a and p == b) for b in ORDER] for a in ORDER]
    return {"macro_f1": round(macro_f1(pairs)[0], 4), "accuracy": round(sum(g == p for g, p in pairs) / len(pairs), 4),
            "errors": sum(g != p for g, p in pairs), "confusion_E_C_N": cm,
            "transitions": dict(sorted(Counter(f"{NAME[g]}->{NAME[p]}" for g, p in pairs if g != p).items()))}


def paired(base, cand, ids):
    b, c = pred[base], pred[cand]
    fixed = [i for i in ids if b[i]["label"] != gold[i] and c[i]["label"] == gold[i]]
    broken = [i for i in ids if b[i]["label"] == gold[i] and c[i]["label"] != gold[i]]
    moved = [i for i in ids if b[i]["label"] != gold[i] != c[i]["label"] and b[i]["label"] != c[i]["label"]]
    fmt = lambda i: f"{NAME[gold[i]]}: {NAME[b[i]['label']]}->{NAME[c[i]['label']]}"
    return {"labels_changed": sum(b[i]["label"] != c[i]["label"] for i in ids), "fixed": len(fixed), "broken": len(broken),
            "wrong_to_other_wrong": len(moved),
            "fixed_by_transition": dict(Counter(fmt(i) for i in fixed)), "broken_by_transition": dict(Counter(fmt(i) for i in broken)),
            "moved_by_transition": dict(Counter(fmt(i) for i in moved)),
            "broken_ids": broken, "fixed_ids": fixed}


for panel in ("representative", "baseline_error_diagnostic"):
    ids = sorted(i for i in sel if sel[i]["panel"] == panel)
    out["panels"][panel] = {
        "n": len(ids),
        "runs": {n: stats(n, ids) for n in RUNS},
        "noise_baseline_vs_repeat": paired("baseline", "baseline_repeat", ids),
        "skill_vs_repeat": paired("baseline_repeat", "skill", ids),
        "skill_vs_baseline": paired("baseline", "skill", ids),
        "relation_vs_baseline": paired("baseline", "relation_prompt", ids),
        "errors_by_claim_type": {n: dict(sorted(Counter(sel[i]["claim_type"] for i in ids if pred[n][i]["label"] != gold[i]).items()))
                                 for n in RUNS},
    }
ids = sorted(sel)
out["panels"]["all_180_descriptive"] = {"n": len(ids), "runs": {n: stats(n, ids) for n in RUNS}}

for n in RUNS:
    m = [p["metrics"] for p in pred[n].values()]
    score = json.load(open(HERE / f"runs/{n}/score.official.json", encoding="utf-8"))["tasks"]["A"]
    run = json.load(open(HERE / f"runs/{n}/run.json", encoding="utf-8"))
    out["runs"][n] = {"input_tokens_mean": round(sum(x["input_tokens"] for x in m) / len(m), 1),
                      "output_tokens_mean": round(sum(x["output_tokens"] for x in m) / len(m), 1),
                      "inference_ms_mean": round(sum(x["inference_time_ms"] for x in m) / len(m)),
                      "evidence_found": f"{score['evidence']['found']}/{score['evidence']['cases']}",
                      "evidence_score": round(score["evidence_score"], 4), "cli_timing": run.get("cli_timing"),
                      "api_failures_logged": run.get("api_failures_logged"), "cases_failed_in_cli": run.get("cases_failed_in_cli"),
                      "overrides": run.get("overrides"), "query_cache_dir": run.get("query_cache_dir"),
                      "src_uncommitted_changes": run.get("src_uncommitted_changes"), "commit": run.get("commit", "")[:7]}

(HERE / "skill_screen_analysis.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "panels"}, indent=1, ensure_ascii=False))
for panel, d in out["panels"].items():
    print(f"\n=== {panel} (n={d['n']})")
    for n, s in d["runs"].items():
        print(f"  {n:16s} F1 {s['macro_f1']:.4f} Acc {s['accuracy']:.4f} Fehler {s['errors']:2d} CM(E,C,N) {s['confusion_E_C_N']} {s['transitions']}")
    for key in ("noise_baseline_vs_repeat", "skill_vs_repeat", "skill_vs_baseline", "relation_vs_baseline"):
        if key in d:
            p = d[key]
            print(f"  {key:26s} geändert {p['labels_changed']:2d} korrigiert {p['fixed']} neu falsch {p['broken']} falsch->anders falsch {p['wrong_to_other_wrong']} "
                  f"| korr. {p['fixed_by_transition']} | neu {p['broken_by_transition']} | versch. {p['moved_by_transition']}")
    if "errors_by_claim_type" in d:
        print("  Fehler nach Claim-Typ:", d["errors_by_claim_type"])
