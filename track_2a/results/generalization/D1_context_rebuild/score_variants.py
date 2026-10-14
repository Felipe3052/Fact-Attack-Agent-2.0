"""Task A variants against the submission run: paired label changes and the estimated change of the total score.

Score = 0.4 S_B + 0.6 S_A, S_A = 0.50 F1 + 0.20 evidence + 0.15 T + 0.15 K, K = best tokens / ours (in + out).
The best team's task A tokens are assumed to be BEST (default 1,266, the lowest published value we know); T is
taken as unchanged. usage: python score_variants.py <track_2a> <baseline run> <run> [<run> ...]
"""
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]); G = ROOT / "results" / "generalization"
BEST = 1266.0
gold = {g["id"]: g["label"] for g in map(json.loads, open(ROOT / ".cache/gen/data/subsets/A/expected-labels.jsonl", encoding="utf-8"))}


def load(name):
    preds = {p["id"]: p for p in map(json.loads, open(G / name / "predictions.jsonl", encoding="utf-8"))}
    a = json.loads((G / name / "score.official.json").read_text(encoding="utf-8"))["tasks"]["A"]
    tin = sum(p["metrics"]["input_tokens"] for p in preds.values()) / len(preds)
    tout = sum(p["metrics"]["output_tokens"] for p in preds.values()) / len(preds)
    return preds, a["macro_f1"], a["evidence_score"], tin, tout


def s_a(f1, ev, tokens):
    return 0.5 * f1 + 0.2 * ev + 0.15 * min(1.0, BEST / tokens)


base = load(sys.argv[2])
sa0 = s_a(base[1], base[2], base[3] + base[4])
print(f"{'run':34s} {'F1':>6s} {'Hit@5':>6s} {'in':>6s} {'out':>5s} {'fix/brk':>8s} {'dScore':>7s}")
print(f"{sys.argv[2]:34s} {base[1]:6.4f} {base[2]:6.4f} {base[3]:6.0f} {base[4]:5.1f} {'':>8s} {0:+7.4f}")
for name in sys.argv[3:]:
    if not (G / name / "score.official.json").exists():
        print(f"{name:34s} (not finished)")
        continue
    r = load(name)
    fixed = sum(base[0][i]["label"] != gold[i] and r[0][i]["label"] == gold[i] for i in gold)
    broke = sum(base[0][i]["label"] == gold[i] and r[0][i]["label"] != gold[i] for i in gold)
    d = 0.6 * (s_a(r[1], r[2], r[3] + r[4]) - sa0)
    print(f"{name:34s} {r[1]:6.4f} {r[2]:6.4f} {r[3]:6.0f} {r[4]:5.1f} {fixed:>3d}/{broke:<4d} {d:+7.4f}")
