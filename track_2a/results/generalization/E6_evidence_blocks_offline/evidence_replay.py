"""Offline Hit@5 replay of evidence compositions on fixed B0 citations (labels/tokens unchanged)."""
import json, os, sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
os.environ['BOOKLET_CACHE_DIR'] = '.cache/gen/booklets'
sys.path.insert(0, '.')
from src.evidence import terms, construct_evidence, ParsedSourcePages
from src.text_utils import official_normalize as normalize
from vendor.hackapertus_starter.evaluate import quote_matches
S = str(Path(__file__).resolve().parent)  # usage (from track_2a): python results/generalization/E6_evidence_blocks_offline/evidence_replay.py
rows = {json.loads(x)['id']: json.loads(x) for x in open(Path(__file__).resolve().parents[1] / 'D0_error_diagnosis' / 'diag_B0.jsonl', encoding='utf-8')}
cases = {c['id']: c for c in map(json.loads, open('.cache/gen/data/cases.jsonl', encoding='utf-8')) if 'booklet' in c}
gold = {g['id']: g for g in map(json.loads, open('.cache/gen/data/expected-labels.jsonl', encoding='utf-8'))}
preds = {p['id']: p for p in map(json.loads, open('results/generalization/B0_submission/predictions.jsonl', encoding='utf-8'))}

def compose(case, cited, pages, variant):
    full, blocks = [], []
    q, v = terms(case['claim']['text']), terms(case.get('vote', ''))
    for pr, n in enumerate(cited):
        page = pages[str(n)]
        if page['text'].strip() and len(normalize(page['text'])) <= 5000:
            full.append({'page': n, 'text': page['text']})
        for o, b in enumerate(page['blocks']):
            if not 80 <= len(normalize(b)) <= 5000: continue
            t = terms(b); sc = sum(3 if w.isdigit() else 1 for w in q & t) + 0.5 * len(v & t)
            blocks.append((sc, -pr, -o, {'page': n, 'text': b}))
    ranked = [b[3] for b in sorted(blocks, key=lambda b: b[:3], reverse=True)]
    nf = {'F3B2': 3, 'F2B3': 2, 'F1B4': 1, 'F0B5': 0}[variant]
    cand = full[:nf] + ranked[:5 - nf] + full[nf:] + ranked[5 - nf:]
    out, seen = [], set()
    for it in cand:
        k = (it['page'], normalize(it['text']))
        if k not in seen: out.append(it); seen.add(k)
        if len(out) == 5: break
    return out

from src.inference import load_parsed_booklet
from src.pdf_parser import PDFParser
def work(path):
    pages = load_parsed_booklet('.cache/gen/data/' + path, PDFParser())['source_pages']
    res = []
    for cid, c in cases.items():
        if c['booklet']['path'] != path or gold[cid]['label'] not in (0, 2): continue
        p = preds[cid]
        cited = list(dict.fromkeys(e['page'] for e in p['evidence']))
        r = {'id': cid, 'type': rows[cid]['type'], 'fold': rows[cid]['fold']}
        for var in ('F3B2', 'F2B3', 'F1B4', 'F0B5'):
            ev = compose(c, cited, pages, var) if p['label'] != 1 else []
            r[var] = any(quote_matches(e['text'], gold[cid]['reference'], 90, 5000) for e in ev)
        res.append(r)
    return res

if __name__ == '__main__':
    paths = sorted({c['booklet']['path'] for c in cases.values()})
    with ProcessPoolExecutor(14) as ex:
        out = [r for rs in ex.map(work, paths) for r in rs]
    json.dump(out, open(S + '/evidence_replay.json', 'w', encoding='utf-8'))
    for var in ('F3B2', 'F2B3', 'F1B4', 'F0B5'):
        h = sum(r[var] for r in out); base = sum(r['F3B2'] for r in out)
        gain = sum(r[var] and not r['F3B2'] for r in out); loss = sum(r['F3B2'] and not r[var] for r in out)
        folds = collections.defaultdict(lambda: [0, 0])
        for r in out: folds[r['fold']][0] += r[var] - r['F3B2']
        print(f"{var}: Hit@5 {h/len(out):.4f} ({h}/{len(out)})  +{gain}/-{loss}  per-fold delta {dict(sorted((k, v[0]) for k, v in folds.items()))}")
