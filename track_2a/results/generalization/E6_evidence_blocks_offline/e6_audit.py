"""usage (from track_2a): python results/generalization/E6_evidence_blocks_offline/e6_audit.py <run name>

E6 audit, offline: F3B2 (production) vs F0B5 on fixed citations of a run; what does each gained/lost hit consist of?"""
import json, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
S, RUN = str(Path(__file__).resolve().parent), sys.argv[1]
os.environ['BOOKLET_CACHE_DIR'] = '.cache/gen/booklets'
sys.path.insert(0, '.')
sys.path.insert(0, S)
from evidence_replay import compose, cases, gold
from src.inference import load_parsed_booklet
from src.pdf_parser import PDFParser
from vendor.hackapertus_starter.evaluate import quote_matches, normalize
preds = {p['id']: p for p in map(json.loads, open(f'results/generalization/{RUN}/predictions.jsonl', encoding='utf-8'))}
diag = {json.loads(x)['id']: json.loads(x) for x in open(Path(__file__).resolve().parents[1] / 'D0_error_diagnosis' / 'diag_B0.jsonl', encoding='utf-8')}

def body(ref, vote):
    lines = ref.split('\n')
    for k in range(1, len(lines) + 1):
        if len(normalize('\n'.join(lines[:k]))) >= len(normalize(vote)):
            return '\n'.join(lines[k:]).strip() if normalize('\n'.join(lines[:k])).startswith(normalize(vote)) else ref
    return ref

def work(path):
    pages = load_parsed_booklet('.cache/gen/data/' + path, PDFParser())['source_pages']
    res = []
    for cid, c in cases.items():
        if c['booklet']['path'] != path or gold[cid]['label'] not in (0, 2): continue
        p = preds[cid]
        if p['label'] == 1:
            res.append({'id': cid, 'base': False, 'f0b5': False, 'fold': diag[cid]['fold'], 'type': diag[cid]['type']}); continue
        cited = list(dict.fromkeys(e['page'] for e in p['evidence']))
        ref = gold[cid]['reference']; bod = body(ref, c['vote'])
        gp = {g['page'] for g in diag[cid]['gold_pages']}
        r = {'id': cid, 'type': diag[cid]['type'], 'fold': diag[cid]['fold']}
        for var, key in (('F3B2', 'base'), ('F0B5', 'f0b5')):
            ev = compose(c, cited, pages, var)
            m = [e for e in ev if quote_matches(e['text'], ref, 90, 5000)]
            r[key] = bool(m)
            if m:
                e = m[0]
                r[key + '_detail'] = {'page': e['page'], 'on_gold_page': e['page'] in gp, 'chars': len(normalize(e['text'])),
                                      'matches_body_only': quote_matches(e['text'], bod, 90, 5000),
                                      'whole_page': e['text'] == pages[str(e['page'])]['text']}
        res.append(r)
    return res

if __name__ == '__main__':
    assert all(preds[i]['label'] in (0, 1, 2) for i in preds)
    paths = sorted({c['booklet']['path'] for c in cases.values()})
    with ProcessPoolExecutor(14) as ex:
        out = [r for rs in ex.map(work, paths) for r in rs]
    Path(S, f'audit_{RUN}.json').write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    base, f = sum(r['base'] for r in out), sum(r['f0b5'] for r in out)
    gain = [r for r in out if r['f0b5'] and not r['base']]; loss = [r for r in out if r['base'] and not r['f0b5']]
    print(f"{RUN}: Hit@5 Produktion {base}/{len(out)} = {base/len(out):.4f}  |  F0B5 {f}/{len(out)} = {f/len(out):.4f}  |  +{len(gain)} / -{len(loss)}")
    for name, L, key in (('gewonnen', gain, 'f0b5_detail'), ('verloren', loss, 'base_detail')):
        d = [r[key] for r in L]
        print(f"  {name}: nur Titel/kein Bodytreffer {sum(not x['matches_body_only'] for x in d)}, auf Gold-Seite {sum(x['on_gold_page'] for x in d)}, "
              f"ganze Seite {sum(x['whole_page'] for x in d)}, Zeichen median {sorted(x['chars'] for x in d)[len(d)//2] if d else '-'}, Typen {dict(collections.Counter(r['type'] for r in L))}")
    allb = [r['f0b5_detail'] for r in out if r['f0b5']]; allp = [r['base_detail'] for r in out if r['base']]
    print(f"  alle Treffer ohne Bodytreffer (Titel-Artefakt): Produktion {sum(not x['matches_body_only'] for x in allp)}, F0B5 {sum(not x['matches_body_only'] for x in allb)}")
    fd = collections.Counter(); 
    for r in out: fd[r['fold']] += r['f0b5'] - r['base']
    print("  Delta pro Fold:", dict(sorted(fd.items())))
    # Bereinigt: nur Treffer zählen, die den Gold-Text ohne Titelpräfix treffen
    cb = sum(r['base'] and r['base_detail']['matches_body_only'] for r in out)
    cf = sum(r['f0b5'] and r['f0b5_detail']['matches_body_only'] for r in out)
    print(f"  bereinigt (nur Body-Treffer): Produktion {cb}/{len(out)} = {cb/len(out):.4f} | F0B5 {cf}/{len(out)} = {cf/len(out):.4f}")
