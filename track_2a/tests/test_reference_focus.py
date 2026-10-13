"""Task B: a long reference is sent as its opening plus the chunks that best match the claim (REFERENCE_MAX_CHARS)."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config
from src.apertus_client import ApertusClient, NLIOutput
from src.inference import ClaimVerificationEngine


class RecordingClient(ApertusClient):
    def __init__(self, translation=None):
        super().__init__(mock=True)
        self.translation, self.translation_calls, self.passages = translation, 0, []

    def translate(self, text, target_lang):
        self.translation_calls += 1
        return self.translation, 4, 5, 10

    def infer(self, context, claim, passages=None, **kwargs):
        self.passages.append(passages)
        return NLIOutput(label=1, reasoning="fixture", p_neutral=1, tokens_prompt=40, tokens_completion=15, tokens_total=55)


# 12 paragraphs of ~300 characters: an opening, one paragraph about the claim's subject, ten unrelated ones
OPENING = "Bundesgesetz über die Untermiete. " + "Ausgangslage und Überblick über die Vorlage. " * 6
RELEVANT = "Mieterinnen und Mieter brauchen künftig die schriftliche Zustimmung des Vermieters zur Untermiete. " * 3
FILLER = [f"Absatz {i}: " + "Die Verfassung regelt die Zuständigkeiten von Bund und Kantonen im Strassenverkehr. " * 3
          for i in range(10)]
REFERENCE = "\n\n".join([OPENING] + FILLER[:5] + [RELEVANT] + FILLER[5:])
CLAIM = "Für eine Untermiete braucht es künftig die schriftliche Zustimmung des Vermieters."


class TestReferenceFocus(unittest.TestCase):
    def run_premise(self, max_chars, claim=CLAIM, translation=None):
        client = RecordingClient(translation)
        engine = ClaimVerificationEngine(apertus_client=client)
        with tempfile.TemporaryDirectory() as directory, patch.object(config, "REFERENCE_MAX_CHARS", max_chars), patch.object(config, "REFERENCE_MID_CHARS", 0), \
                patch.object(config, "QUERY_TRANSLATION_CACHE_DIR", Path(directory)), \
                patch.object(config, "RETRIEVAL_QUERY_MODE", "union"):
            result = engine.verify_premise(claim=claim, reference=REFERENCE, case_id="b-1")
        sent = [p.split(") ", 1)[-1] if p.startswith("(") else p for p in client.passages[0]]
        return result, sent, client

    def test_off_sends_the_whole_reference(self):
        _, sent, client = self.run_premise(0)
        self.assertEqual(len(sent), 12)
        self.assertEqual(client.translation_calls, 0)

    def test_long_reference_keeps_opening_and_matching_chunk_within_budget(self):
        result, sent, client = self.run_premise(1000)
        self.assertLessEqual(sum(len(s) for s in sent), 1000)
        self.assertEqual(sent[0], " ".join(OPENING.split()))
        self.assertIn(" ".join(RELEVANT.split()), sent)
        order = [" ".join(REFERENCE.split("\n\n")[i].split()) for i in range(12)]
        self.assertEqual(sent, [c for c in order if c in sent])  # document order
        self.assertEqual(client.translation_calls, 0)  # same language: no translation
        self.assertEqual(result.tokens_total, 55)

    def test_tiered_budget_applies_only_up_to_the_long_threshold(self):
        engine = ClaimVerificationEngine(apertus_client=RecordingClient(None))
        with patch.object(config, "REFERENCE_MAX_CHARS", 6000), patch.object(config, "REFERENCE_MID_CHARS", 3000),                 patch.object(config, "REFERENCE_LONG_CHARS", 9000):
            self.assertEqual(engine._reference_budget(5000), 3000)
            self.assertEqual(engine._reference_budget(9000), 3000)
            self.assertEqual(engine._reference_budget(9001), 6000)
        with patch.object(config, "REFERENCE_MAX_CHARS", 6000), patch.object(config, "REFERENCE_MID_CHARS", 0):
            self.assertEqual(engine._reference_budget(5000), 6000)

    def test_other_language_claim_uses_its_translation_and_counts_its_tokens(self):
        claim = "Pour une sous-location, l'accord écrit du bailleur sera désormais nécessaire."
        result, sent, client = self.run_premise(1000, claim=claim, translation=CLAIM)
        self.assertEqual(client.translation_calls, 1)
        self.assertIn(" ".join(RELEVANT.split()), sent)
        self.assertEqual(result.tokens_total, 55 + 9)


if __name__ == "__main__":
    unittest.main()
