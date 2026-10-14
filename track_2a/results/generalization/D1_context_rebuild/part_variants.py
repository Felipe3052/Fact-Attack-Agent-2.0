"""Offline: does another selection inside an over-budget part keep the gold text? No Apertus calls.

usage: python part_variants.py <track_2a> <gen|ho> <rows.jsonl from retrieval_miss.py> <out.json>
"""
import collections
import json
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
SET, ROWS, OUT = sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
sys.path.insert(0, str(ROOT))
from tests.test_submission_config import submission_settings  # noqa: E402

DATA = ROOT / ".cache" / ("gen/data" if SET == "gen" else "holdout_2026-09-27")
QCACHE = ROOT / ".cache" / "gen" / "queries" / ("E12_section_route" if SET == "gen" else "HO_E12_section_route")
os.environ.update(submission_settings())
os.environ.update(MOCK_APERTUS="true", QUERY_TRANSLATION_CACHE_DIR=str(QCACHE),
                  BOOKLET_CACHE_DIR=str(ROOT / ".cache" / "gen" / "booklets"),
                  BOOKLET_CACHE_PREBUILT=str(ROOT / ".cache" / "gen" / "none"))

from src import part_context  # noqa: E402
from src.inference import ClaimVerificationEngine  # noqa: E402
from src.retriever import PassageRetriever  # noqa: E402
from src.text_utils import clip_to_query, guess_language, split_evenly  # noqa: E402
from vendor.hackapertus_starter.evaluate import normalize  # noqa: E402

BUDGET = 6000


def jl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def words(t):
    return set(re.findall(r"\w{4,}", normalize(t)))


def body(ref, vote):
    lines = ref.split("\n")
    for k in range(1, len(lines) + 1):
        head = normalize("\n".join(lines[:k]))
        if len(head) >= len(normalize(vote or "")):
            if head.startswith(normalize(vote or "")):
                return "\n".join(lines[k:]).strip() or ref
            break
    return ref


def fill(ranked, claim, vote, budget):
    """Production fill: best first, last one clipped to what is left, stop under 600 characters."""
    chosen, left = {}, budget
    for p in ranked:
        if left < 600:
            break
        text = p["text"] if len(p["text"]) <= left else clip_to_query(p["text"], f"{claim} {vote or ''}", left)
        chosen[p["key"]] = text
        left -= len(text)
    return chosen


def select(candidates, claim, vote, variants, vote_weight, budget, chunk):
    if chunk:  # pieces of about `chunk` characters, at sentence ends, in reading order
        units = []
        for p in candidates:
            for i, piece in enumerate(split_evenly(p["text"], max(1, math.ceil(len(p["text"]) / chunk)))):
                units.append({"text": piece, "page_number": p["page_number"], "key": (p["page_number"], i)})
    else:
        units = [{**p, "key": (p["page_number"], 0)} for p in candidates]
    if sum(len(u["text"]) for u in units) <= budget:
        return "\n".join(u["text"] for u in units)
    ranked = PassageRetriever(units).retrieve_hybrid(claim, top_k=len(units), target_vote=vote,
                                                     vote_weight=vote_weight, query_variants=variants)
    chosen = fill(ranked, claim, vote, budget)
    return "\n".join(chosen[u["key"]] for u in units if u["key"] in chosen)


VARIANTS = {  # name: (vote_weight, budget for legal text, budget for other parts, chunk size)
    "base": (2.0, BUDGET, BUDGET, 0),
    "vw0": (0.0, BUDGET, BUDGET, 0),
    "vw0_chunk1000": (0.0, BUDGET, BUDGET, 1000),
    "vw2_chunk1000": (2.0, BUDGET, BUDGET, 1000),
    "vw0_chunk600": (0.0, BUDGET, BUDGET, 600),
    "legal9000": (2.0, 9000, BUDGET, 0),
    "vw0_legal9000": (0.0, 9000, BUDGET, 0),
    "vw0_chunk1000_5000": (0.0, 5000, 5000, 1000),
}

rows = {r["id"]: r for r in jl(ROWS)}
cases = {c["id"]: c for c in jl(DATA / "cases.jsonl") if "booklet" in c}
gold = {g["id"]: g for g in jl(DATA / "expected-labels.jsonl")}
engine = ClaimVerificationEngine(strategy="hybrid", prompt_mode="ids")
res = []
for n, cid in enumerate(sorted(cases, key=lambda i: (cases[i]["booklet"]["path"], i)), 1):
    r, c, g = rows[cid], cases[cid], gold[cid]
    if r["route"] != "part":
        continue
    data = engine._get_booklet_data(DATA / c["booklet"]["path"])
    claim, vote = c["claim"]["text"], c.get("vote")
    part, pages = part_context.part_pages(claim, vote, engine._booklet_parts(data))
    by_page = {}
    for p in data["paragraphs"]:
        by_page.setdefault(p["page_number"], p)
    candidates = [by_page[x] for x in pages if x in by_page and by_page[x]["text"].strip()]
    lang, src = c["claim"].get("language"), c["booklet"].get("language")
    variants = None
    if (lang or guess_language(claim)) != (src or guess_language(" ".join(q["text"] for q in data["pages"][:3]))):
        tr, _, _ = engine._translate_query(claim, lang, src)
        variants = [tr] if tr else None
    out = {"id": cid, "part": part, "gold": g["label"], "pred": r["pred"], "hit": r["hit"],
           "over": sum(len(p["text"]) for p in candidates) > BUDGET, "lang": lang, "src": src}
    rw = words(body(g.get("reference") or "", vote)) if g["label"] in (0, 2) else set()
    for name, (vw, b_legal, b_other, chunk) in VARIANTS.items():
        text = select(candidates, claim, vote, variants, vw, b_legal if part == "legal_text" else b_other, chunk)
        cov = round(len(rw & words(text)) / len(rw), 3) if rw else None
        out[name] = {"chars": len(text), "cov": cov}
    res.append(out)
    if n % 200 == 0:
        print(n, flush=True)
OUT.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")

# summary
g02 = [x for x in res if x["gold"] in (0, 2)]
fails = [x for x in g02 if x["base"]["cov"] is not None and x["base"]["cov"] < 0.6 and (x["pred"] != x["gold"] or x["hit"] is False)]
print(f"{SET}: {len(res)} part cases, {sum(x['over'] for x in res)} over budget; base-clipped failures {len(fails)}")
print(f"{'variant':22s} {'cov>=.6 (gold E/C)':>18s} {'base-fails fixed':>16s} {'lost vs base':>12s} {'mean chars':>10s} {'legal chars':>11s}")
for name in VARIANTS:
    ok = sum((x[name]["cov"] or 0) >= 0.6 for x in g02)
    fixed = sum((x[name]["cov"] or 0) >= 0.6 for x in fails)
    lost = sum((x["base"]["cov"] or 0) >= 0.6 and (x[name]["cov"] or 0) < 0.6 for x in g02)
    mean = sum(x[name]["chars"] for x in res) / len(res)
    legal = [x[name]["chars"] for x in res if x["part"] == "legal_text"]
    print(f"{name:22s} {ok:>11d}/{len(g02):<6d} {fixed:>9d}/{len(fails):<6d} {lost:>12d} {mean:>10.0f} {sum(legal)/max(1,len(legal)):>11.0f}")
print("parts of base-clipped failures:", dict(collections.Counter(x["part"] for x in fails)))
