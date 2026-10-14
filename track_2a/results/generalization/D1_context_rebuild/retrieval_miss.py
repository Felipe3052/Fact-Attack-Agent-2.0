"""Task A: how many label errors / Hit@5 misses of the submission (E12) are retrieval misses?

Rebuilds every task A context offline (part selection, else hybrid top 8), no Apertus calls (translations from
the run's query cache). usage: python retrieval_miss.py <track_2a> <set: gen|ho> <out.jsonl>
"""
import collections
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
SET = sys.argv[2]
OUT = Path(sys.argv[3])
sys.path.insert(0, str(ROOT))
from tests.test_submission_config import submission_settings  # noqa: E402

DATA = ROOT / ".cache" / ("gen/data" if SET == "gen" else "holdout_2026-09-27")
RUN = ROOT / "results" / "generalization" / ("E12_part_context" if SET == "gen" else "HO_E12_part_context")
QCACHE = ROOT / ".cache" / "gen" / "queries" / ("E12_section_route" if SET == "gen" else "HO_E12_section_route")
os.environ.update(submission_settings())
os.environ.update(MOCK_APERTUS="true", QUERY_TRANSLATION_CACHE_DIR=str(QCACHE),
                  BOOKLET_CACHE_DIR=str(ROOT / ".cache" / "gen" / "booklets"),
                  BOOKLET_CACHE_PREBUILT=str(ROOT / ".cache" / "gen" / "none"))

from src import config  # noqa: E402
from src.inference import ClaimVerificationEngine, attributed_section  # noqa: E402
from src.text_utils import clip_to_query, guess_language  # noqa: E402
from vendor.hackapertus_starter.evaluate import normalize, quote_matches, quotes_of  # noqa: E402


def jl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def words(t):
    return set(re.findall(r"\w{4,}", normalize(t)))


def body(ref, vote):
    """Gold reference without the leading vote title (as in D0)."""
    lines = ref.split("\n")
    for k in range(1, len(lines) + 1):
        head = normalize("\n".join(lines[:k]))
        if len(head) >= len(normalize(vote or "")):
            if head.startswith(normalize(vote or "")):
                return "\n".join(lines[k:]).strip() or ref
            break
    return ref


cases = {c["id"]: c for c in jl(DATA / "cases.jsonl") if "booklet" in c}
gold = {g["id"]: g for g in jl(DATA / "expected-labels.jsonl")}
preds = {p["id"]: p for p in jl(RUN / "predictions.jsonl")}
engine = ClaimVerificationEngine(strategy="hybrid", prompt_mode="ids")
misses = collections.Counter()

rows = []
for n, cid in enumerate(sorted(cases, key=lambda i: (cases[i]["booklet"]["path"], i)), 1):
    c, g, p = cases[cid], gold[cid], preds[cid]
    pdf = DATA / c["booklet"]["path"]
    data = engine._get_booklet_data(pdf)
    claim, vote = c["claim"]["text"], c.get("vote")
    lang, src = c["claim"].get("language"), c["booklet"].get("language")
    part = engine._part_passages(data, claim, vote, lang, src)
    if part:
        route, ctx = "part", [(q["page_number"], q["text"]) for q in part[0]]
    else:
        variants = None
        src_lang = src or guess_language(" ".join(q["text"] for q in data["pages"][:3]))
        if (lang or guess_language(claim)) != src_lang:
            tr, _, receipt = engine._translate_query(claim, lang or guess_language(claim), src_lang)
            misses["cache_miss"] += not receipt.get("cache_hit")
            variants = [tr] if tr else None
        side = attributed_section(claim)
        got = data["retriever"].retrieve_hybrid(claim, top_k=config.DEFAULT_TOP_K, target_vote=vote,
                                                query_variants=variants,
                                                ensure_sections={side: config.SPEAKER_BOOST} if side and config.SPEAKER_BOOST else None)
        from src.inference import page_char_limit
        q = f"{claim} {vote or ''}"
        route, ctx = "hybrid", [(x["page_number"], clip_to_query(x["text"], q, page_char_limit(r))) for r, x in enumerate(got)]
    ref = body(g.get("reference") or "", vote) if g["label"] in (0, 2) else ""
    gold_in_ctx = None
    gold_anywhere = None
    gold_pages, coverage = [], None
    if ref:
        rw = words(ref)

        def plausible(text):
            w = words(text)
            short, long_ = (rw, w) if len(rw) <= len(w) else (w, rw)
            return bool(short) and len(short & long_) / len(short) >= 0.5

        # gold pages: the page (or one of its blocks) lies inside the reference or contains it (as in D0)
        for num, s in data["source_pages"].items():
            if not plausible(s["text"]):
                continue
            a, b = sorted((s["text"], ref), key=len)
            ok = quote_matches(a, b, 90, 10 ** 6) or any(
                80 <= len(normalize(bl)) and quote_matches(bl, ref, 90, 5000) for bl in s["blocks"])
            if ok:
                gold_pages.append(int(num))
        gold_anywhere = bool(gold_pages)
        ctx_map = dict(ctx)
        hit_pages = [n for n in gold_pages if n in ctx_map]
        gold_in_ctx = bool(hit_pages)
        if hit_pages:  # share of the gold words the (possibly clipped) context pages kept
            kept = set().union(*(words(ctx_map[n]) for n in hit_pages))
            coverage = round(len(rw & kept) / len(rw), 3) if rw else None
    full_ref = g.get("reference") or ""
    hit = any(quote_matches(x, full_ref, 90, 5000) for x in quotes_of(p)) if g["label"] in (0, 2) and full_ref else None
    rows.append({"id": cid, "route": route, "gold": g["label"], "pred": p["label"], "ctx_pages": [a for a, _ in ctx],
                 "ctx_chars": sum(len(t) for _, t in ctx), "gold_in_ctx": gold_in_ctx, "gold_anywhere": gold_anywhere,
                 "gold_pages": gold_pages, "coverage": coverage,
                 "hit": hit, "tokens_in": p["metrics"]["input_tokens"], "lang": lang, "src": src, "claim": claim})
    if n % 100 == 0:
        print(n, flush=True)

OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
print(SET, len(rows), dict(misses))
