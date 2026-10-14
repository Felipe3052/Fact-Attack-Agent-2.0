"""Offline: short task A prompt (with label probabilities) + bias on label 2 and/or escalation to the full prompt.

An escalated case takes the full prompt's label, evidence and tokens from the submission run (E23) in addition to
the short call's tokens (a simulation; the full prompt is nearly deterministic, 3 of 1,488 labels per rerun).
Thresholds are chosen on four date folds and applied to the fifth (5-fold cross-validation by voting date).
usage: python simulate_cascade.py <track_2a> <journal.jsonl> <short run> <full run>
"""
import json
import math
import sys
from itertools import product
from pathlib import Path

ROOT = Path(sys.argv[1]); G = ROOT / "results" / "generalization"
sys.path.insert(0, str(ROOT))
from vendor.hackapertus_starter.evaluate import quote_matches, quotes_of  # noqa: E402

BEST = 1266.0
D = ROOT / ".cache/gen/data/subsets/A"
gold = {g["id"]: g for g in map(json.loads, open(D / "expected-labels.jsonl", encoding="utf-8"))}
fold = {f["id"]: f["fold"] for f in map(json.loads, open(D / "folds.jsonl", encoding="utf-8"))}
journal = {r["id"]: r for r in map(json.loads, open(sys.argv[2], encoding="utf-8"))}
short = {p["id"]: p for p in map(json.loads, open(G / sys.argv[3] / "predictions.jsonl", encoding="utf-8"))}
full = {p["id"]: p for p in map(json.loads, open(G / sys.argv[4] / "predictions.jsonl", encoding="utf-8"))}
ids = sorted(gold)


def hit(p, g):
    return any(quote_matches(q, g["reference"], 90, 5000) for q in quotes_of(p)) if g["label"] in (0, 2) and g.get("reference") else None


H = {i: (hit(short[i], gold[i]), hit(full[i], gold[i])) for i in ids}
tok = {i: (short[i]["metrics"]["input_tokens"] + short[i]["metrics"]["output_tokens"],
           full[i]["metrics"]["input_tokens"] + full[i]["metrics"]["output_tokens"]) for i in ids}


def macro_f1(pairs):
    f = []
    for c in (0, 1, 2):
        tp = sum(g == c and p == c for g, p in pairs); fp = sum(g != c and p == c for g, p in pairs)
        fn = sum(g == c and p != c for g, p in pairs)
        f.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return sum(f) / 3


def decide(i, bias2, theta):
    """(label, hit, tokens, escalated) of case i under a bias on label 2 and an escalation threshold."""
    j = journal[i]; p = j["p"]
    if sum(p) > 0:
        logits = [math.log(max(x, 1e-9)) for x in p]; logits[2] += bias2
        label = max(range(3), key=lambda k: logits[k])
        conf = max(p)
    else:
        label, conf = short[i]["label"], 1.0
    if conf < theta:
        return full[i]["label"], H[i][1], tok[i][0] + tok[i][1], True
    hit_short = H[i][0] if label == short[i]["label"] else (H[i][0] if label != 1 else None)
    return label, hit_short, tok[i][0], False


def evaluate(sub, bias2, theta):
    rows = [decide(i, bias2, theta) for i in sub]
    f1 = macro_f1([(gold[i]["label"], r[0]) for i, r in zip(sub, rows)])
    hits = [r[1] for i, r in zip(sub, rows) if gold[i]["label"] in (0, 2) and gold[i].get("reference")]
    ev = sum(bool(h) for h in hits) / len(hits)
    t = sum(r[2] for r in rows) / len(rows)
    esc = sum(r[3] for r in rows) / len(rows)
    return f1, ev, t, esc, 0.6 * (0.5 * f1 + 0.2 * ev + 0.15 * min(1, BEST / t))


full_rows = [(gold[i]["label"], full[i]["label"]) for i in ids]
f1_full = macro_f1(full_rows)
ev_full = sum(bool(H[i][1]) for i in ids if H[i][1] is not None) / sum(H[i][1] is not None for i in ids)
t_full = sum(tok[i][1] for i in ids) / len(ids)
s_full = 0.6 * (0.5 * f1_full + 0.2 * ev_full + 0.15 * min(1, BEST / t_full))
agree = sum(journal[i]["label"] == short[i]["label"] for i in ids)
print(f"journal label = run label: {agree}/{len(ids)}; saturated (max p >= 0.98): "
      f"{sum(max(journal[i]['p']) >= 0.98 for i in ids)}")
print(f"{'config':34s} {'F1':>6s} {'Hit@5':>6s} {'tokens':>7s} {'escal.':>6s} {'dScore vs full':>14s}")
print(f"{'full prompt (E23)':34s} {f1_full:6.4f} {ev_full:6.4f} {t_full:7.0f} {'':>6s} {0:+14.4f}")
grid_b = [0.0, -0.5, -1.0, -1.5, -2.0, -3.0, -4.0]
grid_t = [0.0, 0.6, 0.8, 0.9, 0.95, 0.98, 0.99, 0.999]
for b, t in [(0.0, 0.0), (-1.0, 0.0), (-2.0, 0.0), (0.0, 0.9), (0.0, 0.98), (0.0, 0.999), (-1.0, 0.98)]:
    f1, ev, tk, esc, s = evaluate(ids, b, t)
    print(f"{'bias2 %+.1f, escalate below %.3f' % (b, t):34s} {f1:6.4f} {ev:6.4f} {tk:7.0f} {esc:6.1%} {s - s_full:+14.4f}")
# 5-fold CV by voting date: choose (bias2, theta) on four folds for the best score, apply to the fifth
picked, test_ids, preds = [], [], {}
for k in sorted(set(fold.values())):
    train = [i for i in ids if fold[i] != k]; test = [i for i in ids if fold[i] == k]
    best = max(product(grid_b, grid_t), key=lambda bt: evaluate(train, *bt)[4])
    picked.append(best)
    for i in test:
        preds[i] = decide(i, *best)
rows = [preds[i] for i in ids]
f1 = macro_f1([(gold[i]["label"], preds[i][0]) for i in ids])
hits = [preds[i][1] for i in ids if gold[i]["label"] in (0, 2) and gold[i].get("reference")]
ev = sum(bool(h) for h in hits) / len(hits); tk = sum(r[2] for r in rows) / len(rows); esc = sum(r[3] for r in rows) / len(rows)
s = 0.6 * (0.5 * f1 + 0.2 * ev + 0.15 * min(1, BEST / tk))
print(f"{'5-fold CV (chosen per fold)':34s} {f1:6.4f} {ev:6.4f} {tk:7.0f} {esc:6.1%} {s - s_full:+14.4f}   picked {picked}")
