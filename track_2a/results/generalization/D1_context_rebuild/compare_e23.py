"""Paired comparison base vs treatment on the same cases (plus the saved E12 run as a noise reference)."""
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
GEN = ROOT / "results" / "generalization"


def jl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


for data, base, treat, ref in ((".cache/gen/legal_gen", "E23_legal_base", "E23_legal9000", "E12_part_context"),
                               (".cache/gen/legal_ho", "HO_E23_legal_base", "HO_E23_legal9000", "HO_E12_part_context")):
    if not (GEN / treat / "predictions.jsonl").exists():
        continue
    gold = {g["id"]: g["label"] for g in jl(ROOT / data / "expected-labels.jsonl")}
    runs = {n: {p["id"]: p for p in jl(GEN / n / "predictions.jsonl")} for n in (base, treat, ref)}
    print(f"\n== {treat} vs {base} ({len(gold)} cases)")
    for n in (ref, base, treat):
        preds = runs[n]
        wrong = sum(preds[i]["label"] != gold[i] for i in gold)
        tin = sum(preds[i]["metrics"]["input_tokens"] for i in gold) / len(gold)
        tout = sum(preds[i]["metrics"]["output_tokens"] for i in gold) / len(gold)
        extra = ""
        if n != ref:
            s = json.loads((GEN / n / "score.official.json").read_text(encoding="utf-8"))["tasks"]["A"]
            extra = f" macro-F1 {s['macro_f1']:.3f} Hit@5 {s['evidence_score']:.3f}"
        print(f"  {n:22s} wrong {wrong:3d}  in {tin:7.0f}  out {tout:5.1f}{extra}")
    fixed = [i for i in gold if runs[base][i]["label"] != gold[i] and runs[treat][i]["label"] == gold[i]]
    broke = [i for i in gold if runs[base][i]["label"] == gold[i] and runs[treat][i]["label"] != gold[i]]
    noise = [i for i in gold if runs[base][i]["label"] != runs[ref][i]["label"]]
    print(f"  fixed {len(fixed)}  broke {len(broke)}  | base vs saved E12 label changes (noise): {len(noise)}")
    for i in fixed + broke:
        print(f"   {'fixed' if i in fixed else 'BROKE'} {i}: gold {gold[i]} base {runs[base][i]['label']} -> {runs[treat][i]['label']}")
