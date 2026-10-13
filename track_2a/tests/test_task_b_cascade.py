"""Task B cascade: a short label-only call first, the full prompt again when that answer is not sure (B_ESCALATE_BELOW)."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config
from src.apertus_client import ApertusClient, NLIOutput
from src.inference import ClaimVerificationEngine

REFERENCE = "\n\n".join(f"Absatz {i}: " + "Die Verfassung regelt die Zuständigkeiten im Strassenverkehr. " * 6 for i in range(12))
CLAIM = "Die Verfassung regelt die Zuständigkeiten im Strassenverkehr."


class CascadeClient(ApertusClient):
    def __init__(self, first_probs, first_label=1):
        super().__init__(mock=True)
        self.first_probs, self.first_label = first_probs, first_label
        self.short_calls, self.full_calls, self.short_passages = 0, 0, []

    def infer_label(self, passages, claim, claim_language=None, prompt="topic"):
        self.short_calls += 1
        self.short_passages.append(passages)
        p = self.first_probs
        return NLIOutput(label=self.first_label, reasoning="short", p_entail=p[0], p_neutral=p[1], p_contra=p[2],
                         tokens_prompt=300, tokens_completion=2, tokens_total=302)

    def infer(self, context, claim, passages=None, **kwargs):
        self.full_calls += 1
        return NLIOutput(label=2, reasoning="full", p_contra=1.0, tokens_prompt=900, tokens_completion=60,
                         tokens_total=960)


def run(client, escalate_below=0.98, short_chars=2000):
    engine = ClaimVerificationEngine(apertus_client=client)
    with tempfile.TemporaryDirectory() as directory, patch.object(config, "B_PROMPT", "topic"), \
            patch.object(config, "B_ESCALATE_BELOW", escalate_below), patch.object(config, "B_SHORT_CHARS", short_chars), \
            patch.object(config, "REFERENCE_MID_CHARS", 3000), patch.object(config, "QUERY_TRANSLATION_CACHE_DIR", Path(directory)):
        return engine.verify_premise(claim=CLAIM, reference=REFERENCE, case_id="b-1")


class FailingFullClient(CascadeClient):
    def infer(self, context, claim, passages=None, **kwargs):
        self.full_calls += 1
        return NLIOutput(label=1, reasoning="API Error", error="api: boom", tokens_prompt=0, tokens_completion=0,
                         tokens_total=0)


class TestTaskBCascade(unittest.TestCase):
    def test_failed_second_call_keeps_the_first_answer(self):
        client = FailingFullClient((0.1, 0.2, 0.7), first_label=2)
        result = run(client)
        self.assertEqual((client.short_calls, client.full_calls), (1, 1))
        self.assertEqual(result.label, 2)  # not the neutral fallback of the failed call
        self.assertEqual(result.tokens_total, 302)

    def test_failed_first_and_second_call_fall_back_to_neutral(self):
        client = FailingFullClient((0.0, 0.0, 0.0), first_label=1)
        client.infer_label = lambda *a, **k: NLIOutput(label=1, reasoning="API Error", error="api: boom")
        result = run(client)
        self.assertEqual(result.label, 1)
        self.assertEqual(client.full_calls, 1)

    def test_sure_short_answer_is_final_and_costs_one_call(self):
        client = CascadeClient((0.0, 1.0, 0.0))
        result = run(client)
        self.assertEqual((client.short_calls, client.full_calls), (1, 0))
        self.assertEqual(result.label, 1)
        self.assertEqual(result.tokens_total, 302)

    def test_unsure_short_answer_escalates_and_both_calls_count(self):
        client = CascadeClient((0.0, 0.7, 0.3))
        result = run(client)
        self.assertEqual((client.short_calls, client.full_calls), (1, 1))
        self.assertEqual(result.label, 2)  # the full prompt's answer
        self.assertEqual(result.tokens_total, 302 + 960)

    def test_missing_probabilities_escalate(self):
        client = CascadeClient((0.0, 0.0, 0.0))
        run(client)
        self.assertEqual(client.full_calls, 1)

    def test_threshold_zero_turns_the_cascade_off(self):
        client = CascadeClient((0.0, 0.7, 0.3))
        run(client, escalate_below=0.0)
        self.assertEqual(client.full_calls, 0)

    def test_first_call_sees_the_short_budget(self):
        client = CascadeClient((0.0, 1.0, 0.0))
        run(client, short_chars=2000)
        sent = sum(len(p) for p in client.short_passages[0])
        self.assertLessEqual(sent, 2000)
        self.assertGreater(sent, 0)


if __name__ == "__main__":
    unittest.main()
