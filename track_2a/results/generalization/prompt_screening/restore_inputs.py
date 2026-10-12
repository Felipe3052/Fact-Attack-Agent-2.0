"""Restore input/cases.jsonl and input/expected-labels.jsonl of the frozen 180-case screen from the pinned dataset.

They are not committed (expected-labels.jsonl holds the gold reference passages). Prepare the dataset first:
  python scripts/prepare_competition_cases.py --version v1.1 --scope all --download-booklets --output .cache/gen/data
then, from track_2a:
  python results/generalization/prompt_screening/restore_inputs.py --data .cache/gen/data
Rows follow input/selection.csv; the result is checked against input/restore_check.json (LF line endings, booklet paths
compared as booklets/<file>). Booklet paths are written as absolute paths into --data, as prepare_screen.py did.
"""
import argparse
import csv
import hashlib
import json
import ntpath
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT = HERE / "input"


def read_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def dump(rows):
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, required=True, help="output folder of scripts/prepare_competition_cases.py")
    args = parser.parse_args()
    data = args.data.resolve()
    check = json.loads((INPUT / "restore_check.json").read_text(encoding="utf-8"))
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8")).get("file_hashes")
    if manifest != check["source_case_manifest"]:
        raise SystemExit(f"{data} is not the pinned dataset (manifest {manifest})")
    ids = [r["id"] for r in csv.DictReader(open(INPUT / "selection.csv", encoding="utf-8"))]
    cases = {c["id"]: c for c in read_jsonl(data / "cases.jsonl")}
    gold = {g["id"]: g for g in read_jsonl(data / "expected-labels.jsonl")}
    out_cases = []
    for cid in ids:
        case = json.loads(json.dumps(cases[cid]))
        case["booklet"]["path"] = str((data / case["booklet"]["path"]).resolve())
        out_cases.append(case)
    out_gold = [gold[cid] for cid in ids]

    normalised = [json.loads(json.dumps(c)) for c in out_cases]
    for c in normalised:
        c["booklet"]["path"] = "booklets/" + ntpath.basename(c["booklet"]["path"])
    got = {"expected-labels.jsonl": hashlib.sha256(dump(out_gold).encode()).hexdigest(),
           "cases": hashlib.sha256(dump(normalised).encode()).hexdigest()}
    want = {"expected-labels.jsonl": check["sha256_lf"]["expected-labels.jsonl"],
            "cases": check["sha256_lf_cases_with_booklet_path_as_booklets/<file>"]}
    if got != want:
        raise SystemExit(f"restored inputs differ from the frozen screen: {got} != {want}")
    for name, rows in (("cases.jsonl", out_cases), ("expected-labels.jsonl", out_gold)):
        (INPUT / name).write_text(dump(rows), encoding="utf-8")
    print(f"restored {len(ids)} cases into {INPUT} (hashes match restore_check.json)")


if __name__ == "__main__":
    main()
