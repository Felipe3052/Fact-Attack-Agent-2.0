"""Token breakdown of the recorded task A prompts with the Apertus tokenizer, calibrated against real counts."""
import json, re, statistics, sys
from tokenizers import Tokenizer
tok = Tokenizer.from_file(sys.argv[1])
prompts = [json.loads(x) for x in open(sys.argv[2], encoding="utf-8")]
preds = {p["id"]: p for p in map(json.loads, open(sys.argv[3], encoding="utf-8"))}
cases = {c["id"]: c for c in map(json.loads, open(sys.argv[4], encoding="utf-8"))}
n = lambda s: len(tok.encode(s, add_special_tokens=False).ids)
sys_tokens = n(prompts[0]["system"])
assert all(p["system"] == prompts[0]["system"] for p in prompts)
rows = []
for p in prompts:
    u = p["user"]
    ctx = u.split("=== DOCUMENT CONTEXT ===\n", 1)[1].split("\n\n=== CLAIM ===", 1)[0]
    claim = u.split("=== CLAIM ===\n", 1)[1].split("\n\nDetermine", 1)[0]
    labels = re.findall(r"\[P\d+\] \([^)]*\) ", ctx)
    ws = re.sub(r"[ \t]+", " ", re.sub(r"[ \t]*\n[ \t]*", "\n", ctx))
    ws = re.sub(r"\n{2,}", "\n", ws)
    c = cases[p["id"]]; same = c["claim"]["language"] == c["booklet"]["language"]
    rows.append({"id": p["id"], "user": n(u), "ctx": n(ctx), "claim": n(claim), "labels": sum(n(l) for l in labels),
                 "ctx_ws": n(ws), "chars": len(ctx), "chars_ws": len(ws), "real": preds[p["id"]]["metrics"]["input_tokens"],
                 "out": preds[p["id"]]["metrics"]["output_tokens"], "same": same})
same = [r for r in rows if r["same"]]
overhead = statistics.median(r["real"] - sys_tokens - r["user"] for r in same)
exact = sum(abs(r["real"] - sys_tokens - r["user"] - overhead) <= 2 for r in same)
m = lambda k: statistics.mean(r[k] for r in rows)
print(f"system prompt: {sys_tokens} tokens; chat-template overhead (median, same-language): {overhead}; "
      f"calibration within ±2 tokens: {exact}/{len(same)}")
print(f"mean per case: real input {m('real'):.0f} = system {sys_tokens} + user {m('user'):.0f} (+ template/translation)")
print(f"  user = context {m('ctx'):.0f} (of which page labels '(p. N; section)' {m('labels'):.0f}) + claim {m('claim'):.0f} + framing {m('user')-m('ctx')-m('claim'):.0f}")
print(f"  context with whitespace collapsed: {m('ctx_ws'):.0f} tokens (-{m('ctx')-m('ctx_ws'):.0f}); chars {m('chars'):.0f} -> {m('chars_ws'):.0f}")
print(f"  output tokens mean {m('out'):.1f}")
json.dump(rows, open(sys.argv[5], "w", encoding="utf-8"))
