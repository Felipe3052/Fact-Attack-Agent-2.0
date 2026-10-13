"""Diagnostic: reconstruct every task-A context of the submission configuration offline and map gold to pages.

Writes one JSON line per task-A case with: claim type, gold/predicted labels (B0, B0b), the 8 context pages in prompt
order, the full-ranking rank of every gold page, gold pages, cited pages, Hit@5, and whether page clipping removed the
gold text. Translations for the 'union' ranking are acquired with the production QueryTranslator (cost logged).

usage: python diag_contexts.py <track_2a dir> <out.jsonl>
"""
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2])
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from tests.test_submission_config import submission_settings  # noqa: E402

os.environ.update(submission_settings())
os.environ.update(BOOKLET_CACHE_DIR=str(ROOT / ".cache" / "gen" / "booklets"),
                  BOOKLET_CACHE_PREBUILT=str(ROOT / ".cache" / "gen" / "none"),
                  QUERY_TRANSLATION_CACHE_DIR=str(ROOT / ".cache" / "gen" / "queries" / "diag_contexts"))

from src import config  # noqa: E402
from src.inference import (ClaimVerificationEngine, attributed_section, _LEGAL_TEXT_SECTION)  # noqa: E402
from src.text_utils import clip_to_query, guess_language  # noqa: E402
from vendor.hackapertus_starter.evaluate import normalize, quote_matches, quotes_of  # noqa: E402

assert config.RETRIEVAL_QUERY_MODE == "union" and config.DEFAULT_TOP_K == 8 and config.PAGE_MAX_CHARS == 3000
DATA = ROOT / ".cache" / "gen" / "data"
GEN = ROOT / "results" / "generalization"


def jl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def claim_type(text):
    t = text.lower()
    rules = [("consequence", r"angenommen|accept|si le vote|se il voto|se la votazione|en cas de oui|in caso di s"),
             ("legal_text", r"abstimmungstext|texte soumis|texte de vote|testo di voto|testo sottoposto|gesetzestext|verfassungstext"),
             ("summary", r"zusammenfassung|résumé|riassunto|in kürze|en bref|in breve"),
             ("committee", r"komitee|comit|initiant|urheber|promotori|auteurs"),
             ("federal_council", r"bundesrat|conseil f|consiglio federale|parlament")]
    for name, pattern in rules:
        if re.search(pattern, t):
            return name
    return "other"


def words(text):
    return set(re.findall(r"\w{4,}", normalize(text)))


cases = {c["id"]: c for c in jl(DATA / "cases.jsonl") if "booklet" in c}
gold = {g["id"]: g for g in jl(DATA / "expected-labels.jsonl")}
folds = {f["id"]: f for f in jl(DATA / "folds.jsonl")}
runs = {name: {p["id"]: p for p in jl(GEN / name / "predictions.jsonl")} for name in ("B0_submission", "B0b_repeat")}

engine = ClaimVerificationEngine(strategy="hybrid", prompt_mode="ids")
usage = {"calls": 0, "in": 0, "out": 0, "rejected": 0}
lock = threading.Lock()


def one(cid):
    c = cases[cid]
    pdf = DATA / c["booklet"]["path"]
    data = engine._get_booklet_data(pdf)
    claim, vote = c["claim"]["text"], c.get("vote")
    src_lang = c["booklet"].get("language") or guess_language(" ".join(p["text"] for p in data["pages"][:3]))
    lang = c["claim"].get("language") or guess_language(claim)
    variants = None
    if lang != src_lang:
        translated, (ti, to), receipt = engine._translate_query(claim, lang, src_lang)
        with lock:
            usage["calls"] += 0 if receipt.get("cache_hit") else 1
            usage["in"] += ti
            usage["out"] += to
            usage["rejected"] += bool(receipt.get("rejection"))
        if translated:
            variants = [translated]
    r = data["retriever"]
    side = attributed_section(claim)
    ctx = r.retrieve_hybrid(claim, top_k=8, target_vote=vote, query_variants=variants,
                            ensure_sections={side: config.SPEAKER_BOOST} if side else None)
    full = r.retrieve_hybrid(claim, top_k=len(r.paragraphs), target_vote=vote, query_variants=variants)
    rank_of = {p["page_number"]: i + 1 for i, p in enumerate(full)}
    sources = data["source_pages"]
    g = gold[cid]
    ref = g.get("reference") or ""
    full_ref = ref
    gold_pages = []
    if g["label"] in (0, 2) and ref:
        # every gold reference starts with the vote title; map pages on the passage body only, otherwise any
        # block that just repeats the title would count as a gold page
        lines = ref.split("\n")
        for k in range(1, len(lines) + 1):
            if len(normalize("\n".join(lines[:k]))) >= len(normalize(vote or "")):
                if normalize("\n".join(lines[:k])).startswith(normalize(vote or "")):
                    ref = "\n".join(lines[k:]).strip() or full_ref
                break
        ref_words = words(ref)

        def plausible(text, contains_ref):
            # cheap necessary condition for partial_ratio >= 90: most words of the shorter text occur in the longer
            if os.environ.get("DIAG_NOPREFILTER"):
                return True
            w = words(text)
            short, long_ = (ref_words, w) if contains_ref else (w, ref_words)
            return bool(short) and len(short & long_) / len(short) >= 0.5

        for num, page in sources.items():
            blocks = [b for b in page["blocks"] if 80 <= len(normalize(b)) <= 5000]
            page_ok = (page["text"].strip() and len(normalize(page["text"])) <= 5000
                       and (plausible(page["text"], True) or plausible(page["text"], False))
                       and quote_matches(page["text"], ref, 90, 5000))
            block_hits = [b for b in blocks if plausible(b, False) and quote_matches(b, ref, 90, 5000)]
            if page_ok or block_hits:
                gold_pages.append({"page": int(num), "page_match": bool(page_ok), "n_blocks": len(block_hits),
                                   "words": sorted(set().union(*(words(b) for b in block_hits)) if block_hits else words(ref))})
    query = f"{claim} {vote or ''}"
    clipped = {}
    for p in ctx:
        clipped[p["page_number"]] = (len(p["text"]) > config.PAGE_MAX_CHARS, words(clip_to_query(p["text"], query, config.PAGE_MAX_CHARS)))
    ctx_pages = [p["page_number"] for p in ctx]
    gold_info = []
    for gp in gold_pages:
        n = gp["page"]
        cover = None
        if n in clipped and gp["words"]:
            cover = len(set(gp["words"]) & clipped[n][1]) / len(gp["words"])
        gold_info.append({"page": n, "rank": rank_of.get(n), "in_context": n in clipped,
                          "clipped": clipped[n][0] if n in clipped else None, "coverage": cover,
                          "page_match": gp["page_match"], "n_blocks": gp["n_blocks"]})
    row = {"id": cid, "fold": folds[cid]["fold"], "date": folds[cid]["date"], "src": src_lang, "lang": lang,
           "type": claim_type(claim), "speaker_side": side, "gold": g["label"], "translated": bool(variants),
           "ctx_pages": ctx_pages, "ctx_sections": [p.get("section") for p in ctx],
           "n_legal_in_ctx": sum(p.get("section") == _LEGAL_TEXT_SECTION for p in ctx),
           "gold_pages": gold_info, "claim": claim, "vote": vote}
    for name, preds in runs.items():
        p = preds[cid]
        cited = list(dict.fromkeys(e["page"] for e in p.get("evidence", []) if isinstance(e, dict)))
        hit = any(quote_matches(q, full_ref, 90, 5000) for q in quotes_of(p)) if g["label"] in (0, 2) and full_ref else None
        row[name] = {"label": p["label"], "cited": cited, "hit": hit, "tokens_in": p["metrics"]["input_tokens"],
                     "cited_outside_ctx": [n for n in cited if n not in clipped]}
    return row


def translate_all(ids):
    """Phase 1 (I/O-bound): acquire every needed translation into the on-disk cache, 8 threads."""
    def t(cid):
        c = cases[cid]
        if c["claim"]["language"] != c["booklet"]["language"]:
            engine._translate_query(c["claim"]["text"], c["claim"]["language"], c["booklet"]["language"])
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(t, ids))


def work(group):
    """Phase 2 (CPU-bound, one process per booklet group): translations come from the cache."""
    return [one(cid) for cid in group]


if __name__ == "__main__":
    from concurrent.futures import ProcessPoolExecutor, as_completed
    ids = sorted(cases, key=lambda i: (cases[i]["booklet"]["path"], i))
    done = set()
    if OUT.exists():
        done = {json.loads(x)["id"] for x in OUT.read_text(encoding="utf-8").splitlines() if x.strip()}
    todo = [i for i in ids if i not in done]
    print(f"{len(done)} done, {len(todo)} to do", flush=True)
    translate_all(todo)
    print("translations ready", json.dumps(usage), flush=True)
    groups = {}
    for cid in todo:
        groups.setdefault(cases[cid]["booklet"]["path"], []).append(cid)
    with ProcessPoolExecutor(14) as pool, OUT.open("a", encoding="utf-8") as out:
        futures = [pool.submit(work, g) for g in groups.values()]
        for n, f in enumerate(as_completed(futures), 1):
            for r in f.result():
                out.write(json.dumps(r, ensure_ascii=False) + "\n")
            out.flush()
            print(f"group {n}/{len(futures)} saved", flush=True)
    print("FINISHED", flush=True)
