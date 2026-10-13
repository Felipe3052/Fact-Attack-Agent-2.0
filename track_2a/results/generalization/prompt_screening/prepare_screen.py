"""Freeze a paired Task-A prompt screen before running the candidate prompt.

The primary panel is stratified by date-grouped fold and gold label. A separately
reported diagnostic panel samples known baseline confusions, without inspecting
any output from the candidate prompt.
"""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__import__("os").environ.get("SCREEN_SOURCE_TRACK_2A", ROOT)).resolve()
DATA = SOURCE / ".cache" / "gen" / "data"
OUT = Path(__file__).resolve().parent / "input"
SEED = "20261012-task-a-relation-screen-v1"


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(cid):
    return hashlib.sha256(f"{SEED}:{cid}".encode()).hexdigest()


def main():
    cases_all = read_jsonl(DATA / "cases.jsonl")
    gold_all = read_jsonl(DATA / "expected-labels.jsonl")
    folds_all = read_jsonl(DATA / "folds.jsonl")
    diagnostics = read_jsonl(SOURCE / "results" / "generalization" / "D0_error_diagnosis" / "diag_B0.jsonl")
    baseline = {p["id"]: p for p in read_jsonl(SOURCE / "results" / "generalization" / "B0_submission" / "predictions.jsonl")}
    cases = {c["id"]: c for c in cases_all if "booklet" in c}
    gold = {g["id"]: g for g in gold_all if g["id"].endswith("-A")}
    folds = {f["id"]: f for f in folds_all if f["id"].endswith("-A")}
    diag = {d["id"]: d for d in diagnostics}
    assert len(cases) == len(gold) == len(folds) == len(diag) == 1488
    assert set(cases) == set(gold) == set(folds) == set(diag) == set(baseline.keys() & gold.keys())

    # Primary panel: 8 examples per gold class in each of five date-grouped folds.
    # Within each stratum, stable SHA-256 ordering makes selection reproducible.
    selected = {}
    for fold in range(5):
        for label in range(3):
            pool = [cid for cid in cases if folds[cid]["fold"] == fold and gold[cid]["label"] == label]
            chosen = sorted(pool, key=key)[:8]
            assert len(chosen) == 8
            for cid in chosen:
                selected[cid] = "representative"

    # Diagnostic panel: baseline error transitions proportionally sample the known
    # confusion classes while ensuring each documented transition is represented.
    # These 60 cases are not used as the representative performance estimate.
    target = {(0, 2): 20, (0, 1): 16, (2, 1): 12, (2, 0): 8, (1, 2): 3, (1, 0): 1}
    fold_counts = Counter(folds[cid]["fold"] for cid in selected)
    pair_counts = Counter((diag[cid]["src"], diag[cid]["lang"]) for cid in selected)
    date_counts = Counter(diag[cid]["date"] for cid in selected)
    for (g, p), amount in target.items():
        pool = [cid for cid in cases if cid not in selected and diag[cid]["gold"] == g
                and diag[cid]["B0_submission"]["label"] == p]
        for _ in range(amount):
            if not pool:
                raise ValueError(f"Insufficient cases for baseline confusion {g}->{p}")
            cid = min(pool, key=lambda item: (
                fold_counts[folds[item]["fold"]],
                pair_counts[(diag[item]["src"], diag[item]["lang"])],
                date_counts[diag[item]["date"]], key(item)))
            pool.remove(cid)
            selected[cid] = "baseline_error_diagnostic"
            fold_counts[folds[cid]["fold"]] += 1
            pair_counts[(diag[cid]["src"], diag[cid]["lang"])] += 1
            date_counts[diag[cid]["date"]] += 1
    assert len(selected) == 180

    OUT.mkdir(parents=True, exist_ok=False)
    out_cases, out_gold, out_folds = [], [], []
    with (OUT / "selection.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "panel", "fold", "date", "gold", "baseline_prediction",
                                               "baseline_transition", "language_pair", "claim_type"])
        writer.writeheader()
        for cid in sorted(selected, key=lambda item: (folds[item]["fold"], diag[item]["date"], item)):
            case = dict(cases[cid])
            case["claim"] = dict(case["claim"])
            case["booklet"] = dict(case["booklet"])
            case["booklet"]["path"] = str((DATA / case["booklet"]["path"]).resolve())
            out_cases.append(case)
            out_gold.append(gold[cid])
            out_folds.append(folds[cid])
            d, pred = diag[cid], diag[cid]["B0_submission"]["label"]
            writer.writerow({"id": cid, "panel": selected[cid], "fold": d["fold"], "date": d["date"],
                             "gold": d["gold"], "baseline_prediction": pred,
                             "baseline_transition": f"{d['gold']}->{pred}",
                             "language_pair": f"{d['src']}->{d['lang']}", "claim_type": d["type"]})

    for name, rows in (("cases.jsonl", out_cases), ("expected-labels.jsonl", out_gold), ("folds.jsonl", out_folds)):
        (OUT / name).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    source_run = json.loads((SOURCE / "results" / "generalization" / "B0_submission" / "run.json").read_text(encoding="utf-8"))
    manifest = {
        "purpose": "paired Task-A prompt screen; frozen before candidate evaluation",
        "selection_seed": SEED,
        "dataset": "OST MNLI over Swiss Voting Booklets v1.1",
        "source_case_manifest": source_run["dataset_manifest"],
        "source_B0_commit": source_run["commit"],
        "source_B0_prediction_sha256": digest(SOURCE / "results" / "generalization" / "B0_submission" / "predictions.jsonl"),
        "source_D0_sha256": digest(SOURCE / "results" / "generalization" / "D0_error_diagnosis" / "diag_B0.jsonl"),
        "cases": len(out_cases),
        "panels": {name: sum(value == name for value in selected.values())
                   for name in sorted(set(selected.values()))},
        "representative_design": "5 folds x 3 gold labels x 8 cases = 120; stable hash selection within each cell",
        "diagnostic_confusion_quotas": {f"{a}->{b}": n for (a, b), n in target.items()},
        "fold_counts": dict(sorted(Counter(f["fold"] for f in out_folds).items())),
        "fold_by_date_counts": dict(sorted(Counter(f"{f['fold']}:{diag[f['id']]['date']}" for f in out_folds).items())),
        "language_pair_counts": dict(sorted(Counter(f"{diag[f['id']]['src']}->{diag[f['id']]['lang']}" for f in out_folds).items())),
        "claim_type_counts": dict(sorted(Counter(diag[f["id"]]["type"] for f in out_folds).items())),
        "file_hashes": {name: digest(OUT / name) for name in ("cases.jsonl", "expected-labels.jsonl", "folds.jsonl")},
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("cases", "panels", "fold_counts", "language_pair_counts", "claim_type_counts")},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
