"""Check selected translation cache coverage without permitting network fallback."""
import json
import hashlib
import os
from pathlib import Path

from src.query_translation import QueryTranslator


class CacheMiss(RuntimeError):
    pass


class NoNetworkClient:
    model_name = "swiss-ai/Apertus-v1.5-70B-thinking"

    def translate(self, *args):
        raise CacheMiss("translation missing from the pre-existing cache")


def main():
    cases = [json.loads(line) for line in Path("results/generalization/prompt_screening/input/cases.jsonl")
             .read_text(encoding="utf-8").splitlines() if line.strip()]
    cache = Path(os.environ["QUERY_TRANSLATION_CACHE_DIR"])
    translator = QueryTranslator(NoNetworkClient(), cache)
    cross = [case for case in cases if case["claim"]["language"] != case["booklet"]["language"]]
    hits, misses, rejected, entries = 0, [], 0, []
    for case in cross:
        try:
            _, _, _, receipt = translator.get(case["claim"]["text"], case["claim"]["language"],
                                                case["booklet"]["language"])
            hits += int(receipt["cache_hit"])
            rejected += int(bool(receipt["rejection"]))
            if receipt.get("cache_key"):
                path = cache / (receipt["cache_key"] + ".json")
                entries.append({"key": receipt["cache_key"], "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        except CacheMiss:
            misses.append(case["id"])
    snapshot = hashlib.sha256(json.dumps(sorted(entries, key=lambda x: x["key"]),
                                         sort_keys=True).encode("utf-8")).hexdigest()
    result = {"cross_language_cases": len(cross), "cache_hits": hits,
              "cached_rejections": rejected, "missing_ids": misses,
              "unique_cache_entries": len(entries), "selected_cache_snapshot_sha256": snapshot}
    out = Path("results/generalization/prompt_screening/input/translation_cache_audit.json")
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
