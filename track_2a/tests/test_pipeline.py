"""
Unit tests for end-to-end ClaimVerificationEngine and BenchmarkEvaluator.
"""

import sys
from pathlib import Path
import unittest

_pkg_root = Path(__file__).resolve().parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from src.inference import ClaimVerificationEngine, PredictionResult
from src.evaluator import BenchmarkEvaluator
from src.apertus_client import ApertusClient
from src import config


class TestPipeline(unittest.TestCase):
    def setUp(self):
        # Force mock mode for pipeline tests
        self.mock_client = ApertusClient(mock=True)
        self.engine = ClaimVerificationEngine(apertus_client=self.mock_client)
        self.evaluator = BenchmarkEvaluator(engine=self.engine)
        self.booklet = config.BOOKLETS_DIR / "2026-06-14_de.pdf"

    def test_verify_claim_retrieval(self):
        if not self.booklet.exists():
            self.skipTest(f"Booklet not found at {self.booklet}")

        claim = "Die Initiative verlangt, dass die ständige Wohnbevölkerung vor dem Jahr 2050 zehn Millionen Menschen nicht überschreiten darf."
        res = self.engine.verify_claim(
            claim=claim,
            booklet_pdf=self.booklet,
            claim_language="de",
            strategy="retrieval",
            top_k=3,
        )

        self.assertIsInstance(res, PredictionResult)
        self.assertIn(res.label, (0, 1, 2))
        self.assertEqual(res.strategy, "retrieval")
        self.assertGreater(res.tokens_total, 0)
        self.assertGreater(res.latency_ms, 0)

    def test_verify_claim_full_document(self):
        if not self.booklet.exists():
            self.skipTest(f"Booklet not found at {self.booklet}")

        claim = "Gemäss dem Abstimmungstext soll der Zivildienst angepasst werden."
        res = self.engine.verify_claim(
            claim=claim,
            booklet_pdf=self.booklet,
            claim_language="de",
            strategy="full",
        )

        self.assertIsInstance(res, PredictionResult)
        self.assertIn(res.label, (0, 1, 2))
        self.assertEqual(res.strategy, "full")

    def test_page_char_limit_only_narrows_lower_ranks_when_enabled(self):
        from unittest.mock import patch
        from src.inference import page_char_limit
        with patch("src.config.PAGE_MAX_CHARS", 3000), patch("src.config.PAGE_MAX_CHARS_TAIL", 0), patch("src.config.PAGE_FULL_RANKS", 4):
            self.assertEqual([page_char_limit(r) for r in range(8)], [3000] * 8)  # off: unchanged
        with patch("src.config.PAGE_MAX_CHARS", 3000), patch("src.config.PAGE_MAX_CHARS_TAIL", 1500), patch("src.config.PAGE_FULL_RANKS", 4):
            self.assertEqual([page_char_limit(r) for r in range(8)], [3000] * 4 + [1500] * 4)
        with patch("src.config.PAGE_MAX_CHARS", 1000), patch("src.config.PAGE_MAX_CHARS_TAIL", 1500), patch("src.config.PAGE_FULL_RANKS", 4):
            self.assertEqual(page_char_limit(6), 1000)  # never wider than the general limit

    def test_tail_clipping_narrows_only_task_a_context_pages_after_the_first_four(self):
        if not self.booklet.exists():
            self.skipTest(f"Booklet not found at {self.booklet}")
        import json
        from types import SimpleNamespace
        from unittest.mock import patch
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"label": 0, "p_entail": 1.0, "evidence_ids": [1]}'))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2))

        def run(tail):
            client = ApertusClient(mock=True)
            client.mock = False
            calls = []
            engine = ClaimVerificationEngine(apertus_client=client)
            with patch.object(client, "_create_with_retry", side_effect=lambda **kw: (calls.append(kw), (response, None))[1]), \
                    patch("src.config.PAGE_MAX_CHARS", 3000), patch("src.config.PAGE_MAX_CHARS_TAIL", tail), \
                    patch("src.config.PAGE_FULL_RANKS", 4), patch("src.config.RETRIEVAL_QUERY_MODE", "original"), \
                    patch("src.config.NLI_TOP_K", 8, create=True):
                res = engine.verify_claim(claim="Die Initiative will die Bevölkerung auf 10 Millionen begrenzen.",
                                          booklet_pdf=self.booklet, claim_language="de", strategy="hybrid", top_k=8,
                                          vote="Volksinitiative «Keine 10-Millionen-Schweiz! (Nachhaltigkeitsinitiative)»")
            return res, calls[-1]["messages"][1]["content"], calls[-1]

        off_res, off_ctx, off_call = run(0)
        on_res, on_ctx, on_call = run(1500)
        import re
        split = lambda ctx: re.split(r"\n\n(?=\[P\d+\] )", ctx.split("=== DOCUMENT CONTEXT ===\n", 1)[1].split("\n\n=== CLAIM ===")[0])
        off_p, on_p = split(off_ctx), split(on_ctx)
        self.assertEqual(len(off_p), 8)
        self.assertEqual(len(on_p), 8)
        self.assertEqual(off_p[:4], on_p[:4])  # the first four pages are untouched
        for a, b in zip(off_p[4:], on_p[4:]):
            body = lambda s: s.split(") ", 1)[1] if s.startswith("[P") and ") " in s else s
            self.assertLessEqual(len(body(b)), 1500 + 5)
            self.assertLessEqual(len(b), len(a))
        self.assertLess(len(on_ctx), len(off_ctx))
        self.assertEqual(off_call["messages"][0], on_call["messages"][0])  # system prompt unchanged
        self.assertEqual([s.page_number for s in off_res.evidence_sources], [s.page_number for s in on_res.evidence_sources])
        self.assertEqual(off_res.evidence, on_res.evidence)  # evidence comes from whole pages

    def test_task_a_prompt_switches_never_reach_task_b(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"label": 0, "evidence_ids": [1]}'))],
            usage=SimpleNamespace(prompt_tokens=20, completion_tokens=5, total_tokens=25),
        )
        calls = []
        client = ApertusClient(mock=True)
        client.mock = False
        engine = ClaimVerificationEngine(apertus_client=client)
        with patch.object(client, "_create_with_retry", side_effect=lambda **kw: (calls.append(kw), (response, None))[1]), \
                patch("src.config.A_SKILL_PROMPT", True), patch("src.config.A_RELATION_PROMPT", True), \
                patch("src.config.A_COMPACT_PROMPT", True):
            engine.verify_premise(claim="Der Bundesrat empfiehlt die Ablehnung.", claim_language="de",
                                  reference="Aus Sicht von Bundesrat und Parlament: Empfehlung Nein.", case_id="b-1")
        self.assertTrue(calls)
        for call in calls:
            self.assertNotIn("CLAIM CHECK", call["messages"][0]["content"])
            self.assertNotIn("RELATION CHECK", call["messages"][0]["content"])
            self.assertNotIn("LABEL RULES", call["messages"][0]["content"])

    def test_verify_premise_beginner_task(self):
        claim = "Der Bundesrat empfiehlt die Ablehnung."
        reference = "Aus Sicht von Bundesrat und Parlament bringt die Initiative Unsicherheit. Empfehlung: Nein"
        res = self.engine.verify_premise(
            claim=claim,
            reference=reference,
            claim_language="de",
            case_id="case-0043",
        )

        self.assertIsInstance(res, PredictionResult)
        self.assertEqual(res.id, "case-0043")
        self.assertEqual(res.strategy, "direct_reference")
        self.assertIn(res.label, (0, 1, 2))

        official = res.to_official_dict()
        self.assertEqual(official["id"], "case-0043")
        self.assertIn("label", official)
        self.assertIn("label_name", official)
        self.assertIn("evidence", official)
        self.assertIn("metrics", official)
        self.assertIn("input_tokens", official["metrics"])
        self.assertIn("output_tokens", official["metrics"])
        self.assertIn("inference_time_ms", official["metrics"])

    def test_neutral_evidence_is_strictly_empty(self):
        # A claim unrelated to the booklet should yield neutral and have an empty evidence array
        res = PredictionResult(
            id="case-neutral-1",
            claim="Die Astronauten fliegen zum Mars.",
            label=1,
            label_name="neutral",
            reasoning="Not mentioned in the document",
            evidence=["Some non-empty evidence quote that must be cleared"],
            evidence_sources=[],
            strategy="retrieval",
            booklet_path="dummy.pdf",
            tokens_prompt=100,
            tokens_completion=20,
            tokens_total=120,
            latency_ms=45.0,
        )

        official = res.to_official_dict()
        self.assertEqual(official["label"], 1)
        self.assertEqual(official["label_name"], "neutral")
        self.assertEqual(official["evidence"], [], "Evidence list for Neutral (1) must be strictly []")

    def test_verify_claim_with_vote_target(self):
        if not self.booklet.exists():
            self.skipTest(f"Booklet not found at {self.booklet}")

        claim = "Die Vorlage begrenzt die Zuwanderung vor 2050."
        res = self.engine.verify_claim(
            claim=claim,
            booklet_pdf=self.booklet,
            vote="Nachhaltigkeitsinitiative",
            strategy="retrieval",
            top_k=3,
            case_id="case-0099",
        )

        self.assertEqual(res.id, "case-0099")
        official = res.to_official_dict()
        self.assertEqual(official["id"], "case-0099")
        self.assertIn(official["label"], (0, 1, 2))

    def test_cli_runner_batch_execution(self):
        import json
        import tempfile
        from typer.testing import CliRunner
        from src.cli import app as cli_app

        runner = CliRunner()
        
        # Test 1: Beginner Task input JSON
        sample_input = [
            {
                "id": "case-test-beginner",
                "reference": {"text": "Der Bundesrat empfiehlt Nein zur Initiative."},
                "claim": {"text": "Der Bundesrat empfiehlt die Ablehnung."}
            },
            {
                "id": "case-test-advanced",
                "booklet": {"path": str(self.booklet)},
                "vote": "Nachhaltigkeitsinitiative",
                "claim": {"text": "Die Initiative verlangt 10 Millionen als Obergrenze vor 2050."}
            }
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(sample_input, tf)
            temp_path = tf.name

        try:
            result = runner.invoke(cli_app, ["run", "--input", temp_path, "--mock"])
            self.assertEqual(result.exit_code, 0)
            parsed_output = json.loads(result.output.strip())
            self.assertIsInstance(parsed_output, list)
            self.assertEqual(len(parsed_output), 2)
            self.assertEqual(parsed_output[0]["id"], "case-test-beginner")
            self.assertEqual(parsed_output[1]["id"], "case-test-advanced")
            for item in parsed_output:
                self.assertIn("label", item)
                self.assertIn("label_name", item)
                self.assertIn("evidence", item)
                self.assertIn("metrics", item)
        finally:
            Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

