"""Error categories A-E from diag_B0.jsonl (B0_submission; B0b for stability)."""
import collections
import json
import sys

rows = [json.loads(x) for x in open(sys.argv[1], encoding="utf-8") if x.strip()]
run = sys.argv[2] if len(sys.argv) > 2 else "B0_submission"
print(f"{len(rows)} cases, run {run}")


def cat(r):
    """Primary category of a label error or a Hit@5 miss (gold 0/2)."""
    gp = r["gold_pages"]
    if r["gold"] == 1:
        return "N-gold (no gold page)"
    if not gp:
        return "X: gold text found on no page"
    inctx = [g for g in gp if g["in_context"]]
    if not inctx:
        return "A: gold page not in context"
    if all(g["clipped"] and (g["coverage"] or 0) < 0.6 for g in inctx):
        return "B: gold page in context but clipped away"
    return "C: gold in context"


def tab(title, items, key):
    c = collections.Counter(key(r) for r in items)
    print(f"\n== {title} ({len(items)})")
    for k, v in sorted(c.items(), key=lambda x: -x[1]):
        print(f"  {v:4d}  {k}")


lab = [r for r in rows if r[run]["label"] != r["gold"]]
miss = [r for r in rows if r[run]["hit"] is False]
tab("label errors by category", lab, cat)
tab("label errors by category x type", lab, lambda r: f"{cat(r)[:1]} {r['type']}")
tab("label errors gold->pred", lab, lambda r: f"{r['gold']}->{r[run]['label']}")

def miss_cat(r):
    p = r[run]
    gp = {g["page"] for g in r["gold_pages"]}
    inctx = {g["page"] for g in r["gold_pages"] if g["in_context"]}
    if p["label"] == 1:
        return "M1 predicted neutral (no evidence)" + (" / gold in ctx" if inctx else " / gold NOT in ctx")
    if not gp:
        return "M0 gold text on no page"
    if set(p["cited"]) & gp:
        return "M2 gold page cited, no item matched"
    if inctx:
        return "M3 gold page in context, not cited"
    return "M4 gold page not in context"

tab("Hit@5 misses", miss, miss_cat)
tab("Hit@5 misses x type", miss, lambda r: f"{miss_cat(r)[:2]} {r['type']}")

# Gold-page recall in context for gold 0/2
g02 = [r for r in rows if r["gold"] in (0, 2) and r["gold_pages"]]
rec = sum(any(g["in_context"] for g in r["gold_pages"]) for r in g02) / len(g02)
print(f"\ngold page in context (gold 0/2 with mapped page): {rec:.3f} of {len(g02)}")
for t in sorted({r["type"] for r in g02}):
    s = [r for r in g02 if r["type"] == t]
    print(f"  {t:16s} {sum(any(g['in_context'] for g in r['gold_pages']) for r in s)/len(s):.3f}  n={len(s)}")
# rank of best gold page when absent
ranks = collections.Counter()
for r in g02:
    if not any(g["in_context"] for g in r["gold_pages"]):
        best = min((g["rank"] or 999) for g in r["gold_pages"])
        ranks["9-10" if best <= 10 else "11-12" if best <= 12 else "13-16" if best <= 16 else ">16"] += 1
print("  rank of best gold page when missing:", dict(ranks))
# cited outside context = reconstruction mismatch
mism = sum(bool(r[run]["cited_outside_ctx"]) for r in rows)
print(f"\nreconstruction fidelity: {mism} cases cite a page outside the reconstructed context")
# M2 detail
m2 = [r for r in miss if miss_cat(r).startswith("M2")]
print("M2 gold pages page_match/n_blocks:", collections.Counter((g["page_match"], g["n_blocks"]) for r in m2 for g in r["gold_pages"] if g["page"] in r[run]["cited"]))
# M3 detail: rank of gold page among context, how many pages cited
m3 = [r for r in miss if miss_cat(r).startswith("M3")]
print("M3 n cited:", collections.Counter(len(r[run]["cited"]) for r in m3))
print("M3 gold ctx position:", collections.Counter(min(r["ctx_pages"].index(g["page"]) + 1 for g in r["gold_pages"] if g["in_context"]) for r in m3))
