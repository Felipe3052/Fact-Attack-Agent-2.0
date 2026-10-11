"""
Unit tests for PassageRetriever and Proposal-Aware Isolation.
"""

import sys
from pathlib import Path
import unittest

_pkg_root = Path(__file__).resolve().parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from src.retriever import PassageRetriever


class TestPassageRetriever(unittest.TestCase):
    def setUp(self):
        self.sample_paragraphs = [
            {
                "text": "Erste Vorlage: Volksinitiative «Keine 10-Millionen-Schweiz! (Nachhaltigkeitsinitiative)». Der Bundesrat lehnt die Initiative ab.",
                "page_number": 4,
                "proposal_id": 1,
            },
            {
                "text": "Die Initiative verlangt, dass die ständige Wohnbevölkerung der Schweiz vor dem Jahr 2050 zehn Millionen Menschen nicht überschreiten darf.",
                "page_number": 8,
                "proposal_id": 1,
            },
            {
                "text": "Zweite Vorlage: Änderung des Zivildienstgesetzes. Bundesrat und Parlament wollen den Vollzug des Zivildienstes anpassen.",
                "page_number": 16,
                "proposal_id": 2,
            },
            {
                "text": "Der Zivildienst soll weiterhin als Ersatzdienst für Militärdienstleistende zur Verfügung stehen, jedoch mit strengeren Kriterien.",
                "page_number": 20,
                "proposal_id": 2,
            },
        ]
        self.retriever = PassageRetriever(self.sample_paragraphs)

    def test_tokenization(self):
        tokens = PassageRetriever._tokenize("Schweizer Abstimmungsbüchlein 2026!")
        self.assertIn("schweizer", tokens)
        self.assertIn("abstimmungsbüchlein", tokens)
        self.assertIn("2026", tokens)

    def test_proposal_detection(self):
        # Claim about population/sustainability should target proposal 1
        claim_p1 = "Die Initiative verlangt eine Begrenzung der Wohnbevölkerung auf 10 Millionen Menschen."
        prop_id_1 = self.retriever._detect_proposal(claim_p1)
        self.assertEqual(prop_id_1, 1)

        # Claim about civil service should target proposal 2
        claim_p2 = "Der Bundesrat plant Reformen beim Zivildienst und dessen Vollzug."
        prop_id_2 = self.retriever._detect_proposal(claim_p2)
        self.assertEqual(prop_id_2, 2)

    def test_retrieve_top_k(self):
        claim = "Wie viele Menschen dürfen gemäss Nachhaltigkeitsinitiative vor 2050 in der Schweiz leben?"
        results = self.retriever.retrieve(claim, top_k=2)

        self.assertLessEqual(len(results), 2)
        self.assertGreater(len(results), 0)
        # All retrieved passages should belong to proposal 1 due to proposal-aware routing
        for r in results:
            self.assertEqual(r["proposal_id"], 1)
            self.assertIn("page_number", r)


if __name__ == "__main__":
    unittest.main()


class TestEnsureSections(unittest.TestCase):
    def test_best_pages_of_a_section_replace_the_lowest_ranked(self):
        paras = [{"id": i, "page_number": i, "proposal_id": 1, "section": "COM" if i >= 8 else None,
                  "text": ("Mieten Kündigung Eigenbedarf " * (10 - i)) + f"Seite {i} Text"} for i in range(10)]
        retriever = PassageRetriever(paras)
        plain = retriever.retrieve_hybrid("Mieten Kündigung Eigenbedarf", top_k=4)
        boosted = retriever.retrieve_hybrid("Mieten Kündigung Eigenbedarf", top_k=4, ensure_sections={"COM": 2})
        self.assertEqual(len(boosted), 4)
        self.assertFalse(any(p["section"] == "COM" for p in plain))
        self.assertEqual(sum(p["section"] == "COM" for p in boosted), 2)
        self.assertEqual([p["page_number"] for p in boosted[:2]], [p["page_number"] for p in plain[:2]])

    def test_section_cap_keeps_at_most_n_pages_and_the_context_size(self):
        # pages 0-3 are legal text and rank highest; the cap lets the next-ranked other pages in
        paras = [{"id": i, "page_number": i, "proposal_id": 1, "section": "LEGAL" if i < 4 else None,
                  "text": ("Mieten Kündigung Eigenbedarf " * (10 - i)) + f"Seite {i} Text"} for i in range(10)]
        retriever = PassageRetriever(paras)
        plain = retriever.retrieve_hybrid("Mieten Kündigung Eigenbedarf", top_k=5)
        capped = retriever.retrieve_hybrid("Mieten Kündigung Eigenbedarf", top_k=5, section_caps={"LEGAL": 2})
        self.assertEqual([p["page_number"] for p in plain], [0, 1, 2, 3, 4])
        self.assertEqual([p["page_number"] for p in capped], [0, 1, 4, 5, 6])
        # a cap that is not reached changes nothing
        self.assertEqual(retriever.retrieve_hybrid("Mieten Kündigung Eigenbedarf", top_k=5, section_caps={"LEGAL": 9}), plain)
