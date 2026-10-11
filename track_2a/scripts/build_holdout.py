"""Build the frozen holdout on the 27 September 2026 booklets (not part of the OST dataset) from
data/holdout_2026-09-27/claims.jsonl, in the same case format as scripts/prepare_competition_cases.py.

- Claims were written from the booklet text before any system run on these booklets; each names its basis page.
- Booklet language: rotated within (proposal, claim language) in claim order, so every one of the 9
  source→claim language pairs gets 10 claims.
- Gold reference (as in the dataset): vote title in the booklet language + the PyMuPDF text of the booklet part the
  claim refers to; claims about the consequences of a yes and neutral claims use the detailed explanation.
- This set is meant to be run **once**, at the end, on the final candidate and the baseline. It is development
  tooling and never read by the prediction entrypoint.

Usage: python scripts/build_holdout.py --output .cache/holdout_2026-09-27
"""

import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "holdout_2026-09-27"
DATE = "2026-09-27"
BOOKLETS = {
    "de": ("https://www.admin.ch/dam/de/sd-web/3E6DtQlSES3i/DE-%20Volksabstimmung%20vom%2027.%20September%202026%20-%20"
           "Erl%C3%A4uterungen%20des%20Bundesrates.pdf", "6d27a4c6c5ed0e85"),
    "fr": ("https://www.admin.ch/dam/fr/sd-web/3E6DtQlSES3i/Votation%20populaire%20du%2027%20septembre%202026%20-%20"
           "Explications%20du%20Conseil%20f%C3%A9d%C3%A9ral.pdf", "df3b26401da0189e"),
    "it": ("https://www.admin.ch/dam/it/sd-web/3E6DtQlSES3i/Votazione%20popolare%20del%2027%20settembre%202026%20-%20"
           "Spiegazioni%20del%20Consiglio%20federale.pdf", "e7bfa483ffe46239"),
}
VOTES = {
    "NI": {"de": "Volksinitiative «Wahrung der schweizerischen Neutralität (Neutralitätsinitiative)»",
           "fr": "Initiative populaire « Sauvegarder la neutralité suisse (initiative sur la neutralité) »",
           "it": "Iniziativa popolare «Salvaguardia della neutralità svizzera (Iniziativa sulla neutralità)»"},
    "EI": {"de": "Volksinitiative «Für eine sichere Ernährung – durch Stärkung einer nachhaltigen inländischen Produktion, "
                 "mehr pflanzliche Lebensmittel und sauberes Trinkwasser (Ernährungsinitiative)»",
           "fr": "Initiative populaire «Pour une alimentation sûre – grâce au renforcement de la production indigène "
                 "durable, à davantage de denrées alimentaires végétales et à une eau potable propre (initiative sur "
                 "l’alimentation)»",
           "it": "Iniziativa popolare «Per un’alimentazione sicura – mediante il rafforzamento di una produzione nazionale "
                 "sostenibile, più derrate alimentari vegetali e acqua potabile pulita (Iniziativa sull’alimentazione)»"},
}
# Booklet pages of each part (identical in the three language versions, checked 2026-10-11)
PAGES = {
    "NI": {"summary": [4, 5], "detail": [8, 9, 10, 11, 12], "committee": [14, 15], "federal_council": [16, 17],
           "voting_text": [18, 19]},
    "EI": {"summary": [6, 7], "detail": [20, 21, 22, 23, 24, 25], "committee": [26, 27], "federal_council": [28, 29],
           "voting_text": [30, 31]},
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import pymupdf

    out = args.output.resolve()
    (out / "booklets").mkdir(parents=True, exist_ok=True)
    texts, booklet_hashes = {}, {}
    for lang, (url, prefix) in BOOKLETS.items():
        path = out / "booklets" / f"{DATE}_{lang}.pdf"
        if not path.exists():
            request = urllib.request.Request(url, headers={"User-Agent": "FactAttack-holdout/1.0"})
            with urllib.request.urlopen(request, timeout=90) as response:
                path.write_bytes(response.read())
        raw = path.read_bytes()
        if not raw.startswith(b"%PDF") or not digest(raw).startswith(prefix):
            raise ValueError(f"{path.name} is not the booklet the claims were written for")
        booklet_hashes[path.name] = {"sha256": digest(raw), "url": url}
        with pymupdf.open(path) as document:
            texts[lang] = [page.get_text(sort=True) for page in document]

    claims = [json.loads(line) for line in (SOURCE / "claims.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    order = {}
    cases, expected, folds = [], [], []
    for claim in claims:
        group = (claim["proposal"], claim["claim_language"])
        k = order[group] = order.get(group, -1) + 1
        lang = ("de", "fr", "it")[k % 3]
        part = "detail" if claim["label"] == 1 or claim["section"] == "if_accepted" else claim["section"]
        vote = VOTES[claim["proposal"]][lang]
        reference = vote + "\n\n\n" + "\n".join(texts[lang][p - 1] for p in PAGES[claim["proposal"]][part]).strip()
        for task in ("A", "B"):
            cid = f"holdout-{DATE}-{claim['n']:03d}-{task}"
            case = {"id": cid, "vote": vote, "claim": {"text": claim["claim"], "language": claim["claim_language"]}}
            if task == "A":
                case["booklet"] = {"path": f"booklets/{DATE}_{lang}.pdf", "language": lang}
            else:
                case["reference"] = {"text": reference, "language": lang}
            gold = {"id": cid, "label": claim["label"]}
            if claim["label"] != 1:
                gold["reference"] = reference
            cases.append(case)
            expected.append(gold)
            folds.append({"id": cid, "row": claim["n"], "date": DATE, "fold": 0, "vote": vote, "source_language": lang,
                          "claim_language": claim["claim_language"], "task": task, "section": claim["section"]})
    write_jsonl(out / "cases.jsonl", cases)
    write_jsonl(out / "expected-labels.jsonl", expected)
    write_jsonl(out / "folds.jsonl", folds)
    manifest = {"dataset": f"own holdout, booklets of {DATE}", "claims": len(claims), "case_count": len(cases),
                "claims_sha256": digest((SOURCE / "claims.jsonl").read_bytes()), "booklets": booklet_hashes,
                "file_hashes": {name: digest((out / name).read_bytes())
                                for name in ("cases.jsonl", "expected-labels.jsonl", "folds.jsonl")},
                "historical_test_is_observed": False, "untouched_holdout_available": True}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
