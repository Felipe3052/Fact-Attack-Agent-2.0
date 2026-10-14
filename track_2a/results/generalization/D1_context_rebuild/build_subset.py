"""Subsets of the cases whose voting-text part is over 6,000 characters (the only ones E23 changes).

usage (from track_2a): python results/generalization/D1_context_rebuild/build_subset.py
-> .cache/gen/legal_gen (dataset) and .cache/gen/legal_ho (holdout), for scripts/run_decision.py --data
"""
import collections
import json
import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent


def jl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


for name, src in (("dataset", Path(".cache/gen/data")), ("holdout", Path(".cache/holdout_2026-09-27"))):
    rows = json.loads((HERE / f"part_variants_{name}.json").read_text(encoding="utf-8"))
    ids = {x["id"] for x in rows if x["part"] == "legal_text" and x["over"]}
    dst = Path(".cache/gen") / ("legal_gen" if name == "dataset" else "legal_ho")
    dst.mkdir(parents=True, exist_ok=True)
    rel = os.path.relpath(src, dst).replace("\\", "/")
    cases = [c for c in jl(src / "cases.jsonl") if c["id"] in ids]
    for c in cases:
        c["booklet"]["path"] = f"{rel}/{c['booklet']['path']}"

    def write(f, items):
        (dst / f).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in items), encoding="utf-8")

    write("cases.jsonl", cases)
    for f in ("expected-labels.jsonl", "folds.jsonl"):
        write(f, [r for r in jl(src / f) if r["id"] in ids])
    shutil.copy(src / "manifest.json", dst / "manifest.json")
    labels = collections.Counter(g["label"] for g in jl(dst / "expected-labels.jsonl"))
    print(name, len(cases), "cases, labels", dict(sorted(labels.items())))
