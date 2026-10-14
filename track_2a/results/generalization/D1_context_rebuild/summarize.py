import collections
import json
import sys

rows = [json.loads(x) for x in open(sys.argv[1], encoding="utf-8") if x.strip()]
preds = {}
if len(sys.argv) > 2:  # fidelity: cited pages outside the rebuilt context
    preds = {p["id"]: p for p in map(json.loads, open(sys.argv[2], encoding="utf-8"))}
print(f"{len(rows)} cases; routes", dict(collections.Counter(r["route"] for r in rows)))
if preds:
    out = sum(any(e["page"] not in r["ctx_pages"] for e in preds[r["id"]]["evidence"]) for r in rows)
    print("cases citing a page outside the rebuilt context:", out)
g02 = [r for r in rows if r["gold"] in (0, 2)]
print(f"gold text in context (gold 0/2): {sum(bool(r['gold_in_ctx']) for r in g02)}/{len(g02)}")
for route in ("part", "hybrid"):
    s = [r for r in g02 if r["route"] == route]
    if s:
        print(f"  {route}: {sum(bool(r['gold_in_ctx']) for r in s)}/{len(s)}")


def cat(r):
    if r["gold"] == 1:
        return "gold neutral -> model saw a relation (retrieval irrelevant)"
    if r["gold_in_ctx"] and (r["coverage"] or 0) < 0.6:
        return "gold page in context but clipped (budget/window)"
    if r["gold_in_ctx"]:
        return "gold in context, model wrong"
    if r["gold_anywhere"] is False:
        return "gold text not matchable on any page (parser/reference)"
    return "RETRIEVAL MISS (gold not in context)"


err = [r for r in rows if r["pred"] != r["gold"]]
print(f"\nlabel errors: {len(err)}")
for k, v in collections.Counter(cat(r) for r in err).most_common():
    print(f"  {v:4d}  {k}")
print("  retrieval misses by route:", dict(collections.Counter(r["route"] for r in err if cat(r).startswith("RETR"))))
miss = [r for r in rows if r["hit"] is False]
print(f"\nHit@5 misses: {len(miss)}")
for k, v in collections.Counter(("pred neutral, " if r["pred"] == 1 else "") + cat(r) for r in miss).most_common():
    print(f"  {v:4d}  {k}")
both = [r for r in rows if (cat(r).startswith("RETR") or "clipped" in cat(r)) and (r["pred"] != r["gold"] or r["hit"] is False)]
print(f"\nretrieval misses with label error or Hit@5 miss: {len(both)}")
for r in both[:40]:
    print(f"  {r['id']} {r['route']} {r['lang']}->{r['src']} gold {r['gold']} pred {r['pred']} hit {r['hit']} | {r['claim'][:110]}")
