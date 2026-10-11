"""configs/submission.env must state exactly the defaults of src/config.py (what the Docker image runs)."""

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
ATTRIBUTES = {"NLI_STRATEGY": "DEFAULT_STRATEGY", "NLI_TOP_K": "DEFAULT_TOP_K", "NLI_BATCH_WORKERS": "BATCH_WORKERS"}


def read_env_file(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def effective_config(names, env):
    """The values src.config ends up with in a fresh interpreter, without reading any .env file."""
    code = ("import json, sys, dotenv; dotenv.load_dotenv = lambda *a, **k: False; from src import config; "
            "print(json.dumps({n: getattr(config, n) for n in sys.argv[1:]}))")
    out = subprocess.run([sys.executable, "-c", code, *names], cwd=ROOT, env=env, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def same(value, text):
    if isinstance(value, bool):
        return value == (text.lower() in ("true", "1", "yes"))
    if isinstance(value, (int, float)):
        return float(value) == float(text)
    return str(value) == text


class TestSubmissionConfig(unittest.TestCase):
    def test_submission_env_equals_code_defaults(self):
        stated = read_env_file(ROOT / "configs" / "submission.env")
        clean = {k: v for k, v in os.environ.items() if k in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME")}
        names = {key: ATTRIBUTES.get(key, key) for key in stated}
        defaults = effective_config(sorted(set(names.values())), clean)
        for key, text in stated.items():
            self.assertTrue(same(defaults[names[key]], text), f"{key}: code default {defaults[names[key]]!r}, file {text!r}")


if __name__ == "__main__":
    unittest.main()
