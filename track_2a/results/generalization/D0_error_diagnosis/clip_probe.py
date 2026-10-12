"""Offline probe: does the 3,000-char page window keep the gold text? query = claim+vote (production) vs claim+translation+vote.
No API: translations come from the B0 reconstruction cache (MOCK_APERTUS=true makes a cache miss fail)."""
import json, os, re, sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
ROOT = Path.cwd(); sys.path.insert(0, str(ROOT))
from tests.test_submission_config import submission_settings
os.environ.update(submission_settings())
os.environ.update(BOOKLET_CACHE_DIR=str(ROOT / ".cache/gen/booklets"), BOOKLET_CACHE_PREBUILT=str(ROOT / ".cache/gen/none"),
                  QUERY_TRANSLATION_CACHE_DIR=str(ROOT / ".cache/gen/queries/diag_contexts"), MOCK_APERTUS="true")
from src import config
from src.inference import ClaimVerificationEngine, _PARSE_CACHE_VERSION
from src.text_utils import clip_to_query, normalise
assert _PARSE_CACHE_VERSION == 7  # production parse (main)
DATA = ROOT / ".cache/gen/data"
jl = lambda p: [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]
cases = {c["id"]: c for c in jl(DATA / "cases.jsonl") if "booklet" in c}
gold = {g["id"]: g for g in jl(DATA / "expected-labels.jsonl")}
diag = {r["id"]: r for r in jl(ROOT / "results/generalization/D0_error_diagnosis/diag_B0.jsonl")}
engine = ClaimVerificationEngine(strategy="hybrid", prompt_mode="ids")
norm = lambda t: re.sub(r"\s+", " ", normalise(t)).strip().lower()

def gold_sentences(cid):
    ref = gold[cid]["reference"]; vote = cases[cid]["vote"]
    body = " ".join(ref.split())[len(" ".join(vote.split())):]
    return [norm(s) for s in re.split(r"(?<=[.!?;:])\s+", body) if len(s) >= 40]

def work(path):
    data = engine._get_booklet_data(DATA / path)
    pages = {p["page_number"]: p["text"] for p in data["paragraphs"]}
    out = []
    for cid, c in cases.items():
        if c["booklet"]["path"] != path or gold[cid]["label"] not in (0, 2): continue
        claim, vote = c["claim"]["text"], c["vote"]
        tr = None
        if c["claim"]["language"] != c["booklet"]["language"]:
            tr, _, rec = engine._translate_query(claim, c["claim"]["language"], c["booklet"]["language"])
            assert rec.get("cache_hit")
        gs = gold_sentences(cid)
        for n in diag[cid]["ctx_pages"]:
            text = pages[n]
            if len(text) <= config.PAGE_MAX_CHARS: continue
            on_page = [s for s in gs if s in norm(text)]
            if not on_page: continue
            w0 = norm(clip_to_query(text, f"{claim} {vote}", config.PAGE_MAX_CHARS))
            w1 = norm(clip_to_query(text, f"{claim} {tr or ''} {vote}", config.PAGE_MAX_CHARS))
            out.append({"id": cid, "page": n, "cross": tr is not None, "n_gold_sent": len(on_page),
                        "kept_orig": sum(s in w0 for s in on_page), "kept_tr": sum(s in w1 for s in on_page),
                        "len0": len(w0), "len1": len(w1), "error": diag[cid]["B0_submission"]["label"] != diag[cid]["gold"],
                        "type": diag[cid]["type"]})
    return out

if __name__ == "__main__":
    paths = sorted({c["booklet"]["path"] for c in cases.values()})
    with ProcessPoolExecutor(14) as ex:
        rows = [r for rs in ex.map(work, paths) for r in rs]
    Path(sys.argv[1]).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    def summ(sel, name):
        if not sel: print(name, "keine"); return
        g = sum(r["n_gold_sent"] for r in sel); a = sum(r["kept_orig"] for r in sel); b = sum(r["kept_tr"] for r in sel)
        lost0 = sum(r["kept_orig"] == 0 for r in sel); lost1 = sum(r["kept_tr"] == 0 for r in sel)
        print(f"{name}: Seiten {len(sel)} (Fälle {len({r['id'] for r in sel})}) | Gold-Sätze erhalten: Produktion {a}/{g} = {a/g:.3f}, mit Übersetzung {b}/{g} = {b/g:.3f} | "
              f"Gold-Seite komplett weggeschnitten: {lost0} -> {lost1} | besser/schlechter {sum(r['kept_tr'] > r['kept_orig'] for r in sel)}/{sum(r['kept_tr'] < r['kept_orig'] for r in sel)}")
    summ(rows, "alle gekürzten Gold-Seiten")
    summ([r for r in rows if r["cross"]], "  kreuzsprachig")
    summ([r for r in rows if not r["cross"]], "  gleichsprachig (Kontrolle, Abfrage identisch)")
    summ([r for r in rows if r["error"]], "  Label-Fehler von B0")
    summ([r for r in rows if r["error"] and r["cross"]], "  Label-Fehler, kreuzsprachig")
    print("Fensterlänge Mittel (Zeichen): Produktion", round(sum(r["len0"] for r in rows) / len(rows)), "| Übersetzung", round(sum(r["len1"] for r in rows) / len(rows)))
