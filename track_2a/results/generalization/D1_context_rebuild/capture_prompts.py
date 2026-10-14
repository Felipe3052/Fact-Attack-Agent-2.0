"""Record the exact task A NLI prompts (system + user) of the submission configuration, without calling Apertus.

The client's request function is replaced: NLI requests are recorded and answered with a fixed neutral JSON, any
other request (a translation missing from the cache) is counted and answered empty.
usage: python capture_prompts.py <track_2a> <cases.jsonl> <query cache dir> <out.jsonl>
"""
import json
import os
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(sys.argv[1]).resolve()
CASES, QCACHE, OUT = Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve(), Path(sys.argv[4])
sys.path.insert(0, str(ROOT))
from tests.test_submission_config import submission_settings  # noqa: E402

os.environ.update(submission_settings())
os.environ.update(MOCK_APERTUS="false", API_KEY="offline", BASE_URL="http://offline.invalid/v1",
                  QUERY_TRANSLATION_CACHE_DIR=str(QCACHE), BOOKLET_CACHE_DIR=str(ROOT / ".cache" / "gen" / "booklets"),
                  BOOKLET_CACHE_PREBUILT=str(ROOT / ".cache" / "gen" / "none"))

from src import apertus_client  # noqa: E402
from src.inference import ClaimVerificationEngine  # noqa: E402

lock, current, records, other = threading.Lock(), threading.local(), {}, {"n": 0}


def fake(self, *args, **kwargs):
    messages = kwargs.get("messages") or []
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    user = next((m["content"] for m in messages if m["role"] == "user"), "")
    if "=== DOCUMENT CONTEXT ===" in user:
        with lock:
            records[current.cid] = {"id": current.cid, "system": system, "user": user}
        content = '{"p_entail": 0.0, "p_neutral": 1.0, "p_contra": 0.0, "label": 1, "evidence_ids": []}'
    else:
        with lock:
            other["n"] += 1
        content = ""
    msg = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg, logprobs=None)], usage=None), None


apertus_client.ApertusClient._create_with_retry = fake
engine = ClaimVerificationEngine(strategy="hybrid", prompt_mode="ids")
cases = [json.loads(x) for x in CASES.read_text(encoding="utf-8").splitlines() if x.strip()]
for n, c in enumerate(c for c in cases if "booklet" in c):
    current.cid = c["id"]
    engine.verify_claim(c["claim"]["text"], CASES.parent / c["booklet"]["path"], claim_language=c["claim"].get("language"),
                        vote=c.get("vote"), case_id=c["id"], booklet_language=c["booklet"].get("language"))
    if n % 200 == 0:
        print(n, flush=True)
OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records.values()), encoding="utf-8")
print("recorded", len(records), "other requests (translation cache misses)", other["n"])
