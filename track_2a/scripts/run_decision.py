"""Run one decision run exactly as the jury runs the submission, and keep everything needed to check it later.

- Configuration: configs/submission.env plus explicit --set overrides. Every stated variable is forced into the
  environment, so a developer's .env (e.g. NLI_STRATEGY=retrieval, an 8B model) cannot change the run; the
  effective src.config values are recorded and must equal what was asked for.
- Inference: the official call `python -m src --input ... --output ...` in a subprocess (no gold anywhere near it).
- Scoring: the vendored official evaluate.py, then per date-grouped fold / language pair / class
  (scripts/compare_competition_runs.summarize). Cases the CLI answered only through its failure path are counted.
- Saved under results/generalization/<name>/: predictions, official score, group metrics, run manifest, CLI log.

Usage (from track_2a, after scripts/prepare_competition_cases.py --output .cache/gen/data):
  python scripts/run_decision.py --data .cache/gen/data --name B0 [--task A] [--set NLI_TOP_K=8 ...]
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from tests.test_submission_config import ATTRIBUTES, read_env_file, same  # noqa: E402


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path, rows):
    Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def subset(data, task, limit):
    """cases/expected/folds of one task (or all) in data/subsets/<task>/, booklet paths still relative to it."""
    cases = read_jsonl(data / "cases.jsonl")
    if task != "all":
        cases = [c for c in cases if ("booklet" in c) == (task == "A")]
    if limit:
        cases = cases[:limit]
    ids = {c["id"] for c in cases}
    folder = data / "subsets" / (f"{task}-{limit}" if limit else task)
    folder.mkdir(parents=True, exist_ok=True)
    for c in cases:
        if "booklet" in c:
            c["booklet"]["path"] = os.path.relpath(data / c["booklet"]["path"], folder).replace("\\", "/")
    write_jsonl(folder / "cases.jsonl", cases)
    for name in ("expected-labels.jsonl", "folds.jsonl"):
        write_jsonl(folder / name, [r for r in read_jsonl(data / name) if r["id"] in ids])
    return folder


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, required=True, help="output folder of prepare_competition_cases.py")
    parser.add_argument("--name", required=True)
    parser.add_argument("--task", choices=["A", "B", "all"], default="all")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="override one setting")
    parser.add_argument("--limit", type=int, help="first N cases only (smoke runs, not for decisions)")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results" / "generalization")
    args = parser.parse_args()

    out = args.output_root / args.name
    if out.exists():
        parser.error(f"{out} exists: a decision run is never overwritten, choose a new name")
    data = args.data.resolve()
    folder = subset(data, args.task, args.limit)

    wanted = read_env_file(ROOT / "configs" / "submission.env")
    for item in args.set:
        key, value = item.split("=", 1)
        wanted[key.strip()] = value.strip()
    env = {**os.environ, **wanted, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}  # UTF-8 files as on Linux
    # Private, cold caches per run (translations are re-acquired and their tokens counted); the parse cache is
    # shared, as the image's prebuilt cache is, and keyed by content and parser version
    cache = ROOT / ".cache" / "gen"
    env.update(BOOKLET_CACHE_DIR=str(cache / "booklets"), BOOKLET_CACHE_PREBUILT=str(cache / "none"),
               QUERY_TRANSLATION_CACHE_DIR=str(cache / "queries" / args.name))

    names = {key: ATTRIBUTES.get(key, key) for key in wanted}
    code = ("import json, sys; from src import config; "
            "print(json.dumps({n: getattr(config, n) for n in sys.argv[1:]}))")
    effective = json.loads(subprocess.run([sys.executable, "-c", code, *sorted(set(names.values()))], cwd=ROOT,
                                          env=env, capture_output=True, text=True, check=True).stdout)
    wrong = {k: (effective[names[k]], v) for k, v in wanted.items() if not same(effective[names[k]], v)}
    if wrong:
        raise SystemExit(f"effective configuration differs from the requested one: {wrong}")

    out.mkdir(parents=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "src"], cwd=ROOT, capture_output=True, text=True).stdout
    manifest = {"name": args.name, "task": args.task, "limit": args.limit, "commit": commit,
                "src_uncommitted_changes": bool(dirty.strip()),
                "src_sha256": {p.name: digest(p.read_bytes()) for p in sorted((ROOT / "src").glob("*.py"))},
                "settings": wanted, "overrides": args.set, "effective_config": effective,
                "cases_sha256": digest((folder / "cases.jsonl").read_bytes()),
                "dataset_manifest": json.loads((data / "manifest.json").read_text(encoding="utf-8")).get("file_hashes"),
                "python": sys.version.split()[0], "gold_read_during_inference": False}
    (out / "run.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if dirty.strip():  # uncommitted source changes: keep the exact diff against the recorded commit
        diff = subprocess.run(["git", "diff", "HEAD", "--", "src", "configs"], cwd=ROOT, capture_output=True, text=True).stdout
        (out / "src.diff").write_text(diff, encoding="utf-8")

    started = time.time()
    with open(out / "cli.log", "w", encoding="utf-8") as log:
        code = subprocess.run([sys.executable, "-m", "src", "--input", str(folder / "cases.jsonl"),
                               "--output", str(out / "predictions.jsonl")], cwd=ROOT, env=env, stdout=log,
                              stderr=subprocess.STDOUT).returncode
    wall = time.time() - started
    text = (out / "cli.log").read_text(encoding="utf-8", errors="replace")
    timing = re.search(r"\[timing\] (\d+) cases, wall ([\d.]+) s, non-LLM ([\d.]+) ms/case", text)
    failed = sorted(set(re.findall(r"\[warning\] (\S+?): ", text)))

    evaluate = ROOT / "vendor" / "hackapertus_starter" / "evaluate.py"
    subprocess.run([sys.executable, str(evaluate), "--predictions", str(out / "predictions.jsonl"),
                    "--expected", str(folder / "expected-labels.jsonl"), "--cases", str(folder / "cases.jsonl"),
                    "--json", str(out / "score.official.json")], cwd=ROOT, env=env, capture_output=True, check=True)
    from compare_competition_runs import load, summarize
    groups = summarize(load(out / "predictions.jsonl"), load(folder / "cases.jsonl"),
                       load(folder / "expected-labels.jsonl"), load(folder / "folds.jsonl"))
    groups.pop("case_evidence_hit5", None)
    (out / "groups.json").write_text(json.dumps(groups, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    manifest.update(exit_code=code, wall_seconds_outside=round(wall, 1),
                    cli_timing={"cases": int(timing[1]), "wall_s": float(timing[2]), "non_llm_ms_per_case": float(timing[3])}
                    if timing else None,
                    cases_failed_in_cli=failed, api_failures_logged=text.count("Apertus API failed"))
    (out / "run.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {task: {k: v[k] for k in ("macro_f1", "evidence_hit5", "fold_f1_mean", "fold_f1_std",
                                        "cross_language_macro_f1", "invalid_predictions")}
               for task, v in groups["tasks"].items()}
    print(json.dumps({"name": args.name, "tasks": summary, "cli_timing": manifest["cli_timing"],
                      "cases_failed_in_cli": len(failed)}, indent=2))


if __name__ == "__main__":
    main()
