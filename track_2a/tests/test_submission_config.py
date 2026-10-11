""".env.example must state exactly the defaults of src/config.py (what the Docker image runs)."""

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / ".env.example"
ATTRIBUTES = {"NLI_STRATEGY": "DEFAULT_STRATEGY", "NLI_TOP_K": "DEFAULT_TOP_K", "NLI_WORKERS": "BATCH_WORKERS",
              "NLI_BATCH_WORKERS": "BATCH_WORKERS"}
# Set at run time (endpoint, key) or per environment (cache paths), not part of the pipeline configuration
RUNTIME_ONLY = {"BASE_URL", "API_KEY", "LLM_BASE_URL", "LLM_API_KEY", "BOOKLET_CACHE_DIR", "BOOKLET_CACHE_PREBUILT",
                "QUERY_TRANSLATION_CACHE_DIR"}


def read_env_file(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def submission_settings():
    """The pipeline settings of .env.example (without endpoint, key and cache paths)."""
    return {k: v for k, v in read_env_file(ENV_EXAMPLE).items() if k not in RUNTIME_ONLY}


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
    def test_env_example_equals_code_defaults(self):
        stated = submission_settings()
        clean = {k: v for k, v in os.environ.items() if k in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME")}
        names = {key: ATTRIBUTES.get(key, key) for key in stated}
        defaults = effective_config(sorted(set(names.values())), clean)
        for key, text in stated.items():
            self.assertTrue(same(defaults[names[key]], text), f"{key}: code default {defaults[names[key]]!r}, .env.example {text!r}")

    def test_env_example_at_repository_root_is_the_same_file(self):
        root_copy = ROOT.parent / ".env.example"
        if not root_copy.exists():  # inside the image only track_2a's copy exists
            self.skipTest("no repository root copy")
        self.assertEqual(root_copy.read_text(encoding="utf-8"), ENV_EXAMPLE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
