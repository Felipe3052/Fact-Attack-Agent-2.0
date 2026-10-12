"""Run the two approved 180-case screening runs sequentially with identical inputs: a fresh baseline repeat and
A_SKILL_PROMPT. Both use the same translation cache (read only: every query must be a cache hit) and the same data.

usage (from track_2a, after restore_inputs.py):
  python results/generalization/prompt_screening/launch_skill_screen.py --data <folder with the restored screen inputs>
      --query-cache-dir <translation cache of the B0 reconstruction> [--env-file <.env with BASE_URL / API_KEY>]
The endpoint and key come from the environment (BASE_URL, API_KEY) or from --env-file; they are never written out.
On 2026-10-12 --data was a copy of input/ (cases.jsonl, expected-labels.jsonl, folds.jsonl, manifest.json) and
--query-cache-dir the D0 reconstruction cache `.cache/gen/queries/diag_contexts` of the main checkout.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

TRACK = Path(__file__).resolve().parents[3]
RUNS = Path(__file__).resolve().parent / "runs"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--query-cache-dir", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, help="read BASE_URL / API_KEY from this file instead of the environment")
    args = parser.parse_args()
    secrets = {k: os.environ[k] for k in ("BASE_URL", "API_KEY") if os.environ.get(k)}
    if args.env_file:
        from dotenv import dotenv_values
        secrets.update({k: v for k, v in dotenv_values(args.env_file).items() if k in ("BASE_URL", "API_KEY") and v})
    if set(secrets) != {"BASE_URL", "API_KEY"}:
        raise SystemExit("BASE_URL and API_KEY are required (environment or --env-file)")
    for name, skill in (("baseline_repeat", "false"), ("skill", "true")):
        env = {**os.environ, **secrets, "PYTHONIOENCODING": "utf-8",
               "PROMPT_INPUT_JOURNAL_PATH": str(RUNS / name / "prompt_inputs.jsonl")}
        cmd = [sys.executable, "scripts/run_decision.py", "--data", str(args.data.resolve()), "--task", "A", "--name", name,
               "--output-root", str(RUNS), "--query-cache-dir", str(args.query_cache_dir.resolve()),
               "--set", "A_RELATION_PROMPT=false", "--set", f"A_SKILL_PROMPT={skill}"]
        print(f"START {name}", flush=True)
        code = subprocess.run(cmd, cwd=TRACK, env=env).returncode
        print(f"END {name} exit={code}", flush=True)
        if code != 0:
            sys.exit(code)


if __name__ == "__main__":
    main()
