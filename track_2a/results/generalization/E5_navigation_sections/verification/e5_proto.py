"""Prototype: section of a navigation-header page = section preceding the first listed one (booklet order)."""
import json, glob, collections, re, sys
sys.path.insert(0, '.')
import src.pdf_parser as pp
ORDER = ["Overview / summary", "Official explanation in detail", "Arguments of the initiative/referendum committee",
         "Arguments of the Federal Council and Parliament", "Voting text (legal text)"]
# 'Argumente' alone (newer nav bars: "Argumente 34") = the arguments block, starting with the committee
EXTRA = [("Arguments of the initiative/referendum committee", re.compile(r"\b(?:argumente|arguments|gli\s+argomenti|argomenti)\b", re.I))]

def nav_section(page_text):
    zone = " ".join(" ".join(page_text.splitlines()[:5]).split())
    listed = []
    for label, pattern in pp._SECTION_HEADINGS + EXTRA:
        for m in pattern.finditer(zone):
            if re.match(r"\s*\d", zone[m.end():m.end() + 6]):
                listed.append(ORDER.index(label))
    if not listed:
        return None
    first = min(listed)
    return ORDER[first - 1] if first > 0 else pp.TOC_SECTION

orig = pp.detect_section_heading
def patched(text):
    h = orig(text)
    if h == pp.TOC_SECTION:
        return nav_section(text) or h
    return h

def sections(pages, fn):
    pp.detect_section_heading = fn
    paras = pp.PDFParser().extract_paragraphs("x", passage_chars=None, pages=pages)
    pp.detect_section_heading = orig
    return {p["page_number"]: p["section"] for p in paras}

out = {}
trans = collections.Counter()
for f in sorted(glob.glob('.cache/gen/booklets/*_v7.json')):
    d = json.load(open(f, encoding='utf-8'))
    a, b = sections(d['pages'], orig), sections(d['pages'], patched)
    for n in a:
        if a[n] != b[n]:
            trans[(a[n], b[n])] += 1
    import os; out[os.path.basename(f)[:16]] = {str(n): b[n] for n in b}
for k, v in trans.most_common(): print(v, k)
json.dump(out, open(sys.argv[1] + '/e5_sections.json', 'w'))
