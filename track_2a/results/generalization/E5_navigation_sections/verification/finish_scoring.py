"""Finish a decision run whose inference completed but whose scoring step crashed (same steps as run_decision.py)."""
import json, re, subprocess, sys
from pathlib import Path
ROOT = Path.cwd(); sys.path.insert(0, str(ROOT / "scripts"))
out = ROOT / "results" / "generalization" / sys.argv[1]
folder = ROOT / ".cache" / "gen" / "data" / "subsets" / sys.argv[2]
evaluate = ROOT / "vendor" / "hackapertus_starter" / "evaluate.py"
subprocess.run([sys.executable, str(evaluate), "--predictions", str(out / "predictions.jsonl"), "--expected",
                str(folder / "expected-labels.jsonl"), "--cases", str(folder / "cases.jsonl"),
                "--json", str(out / "score.official.json")], check=True, capture_output=True)
from compare_competition_runs import load, summarize
groups = summarize(load(out / "predictions.jsonl"), load(folder / "cases.jsonl"),
                   load(folder / "expected-labels.jsonl"), load(folder / "folds.jsonl"))
groups.pop("case_evidence_hit5", None)
(out / "groups.json").write_text(json.dumps(groups, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
text = (out / "cli.log").read_text(encoding="utf-8", errors="replace")
timing = re.search(r"\[timing\] (\d+) cases, wall ([\d.]+) s, non-LLM ([\d.]+) ms/case", text)
m = json.loads((out / "run.json").read_text(encoding="utf-8"))
m.update(exit_code=0, cli_timing={"cases": int(timing[1]), "wall_s": float(timing[2]), "non_llm_ms_per_case": float(timing[3])} if timing else None,
         cases_failed_in_cli=sorted(set(re.findall(r"\[warning\] (\S+?): ", text))), api_failures_logged=text.count("Apertus API failed"),
         scoring_note="scoring step re-run with UTF-8 after a cp1252 read error in run_decision.py; inference untouched")
(out / "run.json").write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
t = groups["tasks"]["A"]
print(json.dumps({k: t[k] for k in ("macro_f1", "evidence_hit5", "evidence_found", "fold_f1_mean", "fold_f1_std", "cross_language_macro_f1", "invalid_predictions", "input_tokens_per_case_reported")}, indent=1), m["cli_timing"], "failed:", len(m["cases_failed_in_cli"]), "api_failed:", m["api_failures_logged"])
