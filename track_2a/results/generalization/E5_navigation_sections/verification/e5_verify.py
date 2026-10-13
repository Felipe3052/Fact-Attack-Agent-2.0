"""E5 verification, offline: per-case Hit@5 of E5, label transitions v7 -> v8 cache, context changes caused by the labels.

Context v8 is rebuilt with the same translations as the B0 reconstruction (diag cache), so any context difference to
diag_B0.jsonl comes from the section labels alone (speaker boost reads them), not from translation noise.
usage (from track_2a): python e5_verify.py <scratchpad>
"""
import json, os, sys, glob, collections
from pathlib import Path
S = Path(sys.argv[1])
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from tests.test_submission_config import submission_settings
os.environ.update(submission_settings())
os.environ.update(BOOKLET_CACHE_DIR=str(ROOT / ".cache/gen/booklets"), BOOKLET_CACHE_PREBUILT=str(ROOT / ".cache/gen/none"),
                  QUERY_TRANSLATION_CACHE_DIR=str(ROOT / ".cache/gen/queries/diag_contexts"), MOCK_APERTUS="true")
from src import config
from src.inference import ClaimVerificationEngine, attributed_section, _PARSE_CACHE_VERSION
from vendor.hackapertus_starter.evaluate import quote_matches, quotes_of

assert _PARSE_CACHE_VERSION == 8
DATA = ROOT / ".cache/gen/data"
jl = lambda p: [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]
cases = {c["id"]: c for c in jl(DATA / "cases.jsonl") if "booklet" in c}
gold = {g["id"]: g for g in jl(DATA / "expected-labels.jsonl")}
E5 = {p["id"]: p for p in jl(ROOT / "results/generalization/E5_navigation_sections/predictions.jsonl")}
diag = {r["id"]: r for r in jl(S / "diag_B0.jsonl")}
engine = ClaimVerificationEngine(strategy="hybrid", prompt_mode="ids")


def work(path):
    data = engine._get_booklet_data(DATA / path)
    out = []
    for cid, c in cases.items():
        if c["booklet"]["path"] != path:
            continue
        claim, vote = c["claim"]["text"], c.get("vote")
        variants = None
        if c["claim"]["language"] != c["booklet"]["language"]:
            t, _, rec = engine._translate_query(claim, c["claim"]["language"], c["booklet"]["language"])
            assert rec.get("cache_hit"), "translation must come from the B0 reconstruction cache"
            variants = [t] if t else None
        side = attributed_section(claim)
        ctx = data["retriever"].retrieve_hybrid(claim, top_k=8, target_vote=vote, query_variants=variants,
                                                ensure_sections={side: config.SPEAKER_BOOST} if side else None)
        g = gold[cid]
        p = E5[cid]
        hit = any(quote_matches(q, g["reference"], 90, 5000) for q in quotes_of(p)) if g["label"] in (0, 2) else None
        out.append({"id": cid, "ctx_v8": [x["page_number"] for x in ctx], "sec_v8": [x.get("section") for x in ctx],
                    "ctx_v7": diag[cid]["ctx_pages"], "sec_v7": diag[cid]["ctx_sections"], "hit_E5": hit,
                    "cited_E5": list(dict.fromkeys(e["page"] for e in p.get("evidence", []))),
                    "tokens_E5": p["metrics"]["input_tokens"]})
    return out


if __name__ == "__main__":
    from concurrent.futures import ProcessPoolExecutor
    paths = sorted({c["booklet"]["path"] for c in cases.values()})
    with ProcessPoolExecutor(14) as ex:
        rows = [r for rs in ex.map(work, paths) for r in rs]
    (S / "e5_verify.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    # label transitions between the two parse caches (all pages of all 60 booklets)
    trans = collections.Counter()
    for f7 in glob.glob(str(ROOT / ".cache/gen/booklets/*_v7.json")):
        f8 = f7.replace("_v7.json", "_v8.json")
        a = {p["page_number"]: p["section"] for p in json.load(open(f7, encoding="utf-8"))["paragraphs"]}
        b = {p["page_number"]: p["section"] for p in json.load(open(f8, encoding="utf-8"))["paragraphs"]}
        tx = {n: (p["text"]) for n, p in [(p["page_number"], p) for p in json.load(open(f7, encoding="utf-8"))["paragraphs"]]}
        tx8 = {p["page_number"]: p["text"] for p in json.load(open(f8, encoding="utf-8"))["paragraphs"]}
        trans["page text identical"] += sum(tx[n] == tx8.get(n) for n in tx)
        trans["page text different"] += sum(tx[n] != tx8.get(n) for n in tx)
        for n in a:
            if a[n] != b.get(n):
                trans[(a[n], b.get(n))] += 1
    print("label transitions v7 -> v8:", dict(trans))
    same_ctx = sum(r["ctx_v8"] == r["ctx_v7"] for r in rows)
    print(f"contexts identical (pages+order): {same_ctx}/{len(rows)}; different: {len(rows) - same_ctx}")
    print("cases whose context shows >=1 newly labelled page:",
          sum(any(a is None and b is not None for a, b in zip(r["sec_v7"], r["sec_v8"])) for r in rows if r["ctx_v8"] == r["ctx_v7"]))
    print("FINISHED")
