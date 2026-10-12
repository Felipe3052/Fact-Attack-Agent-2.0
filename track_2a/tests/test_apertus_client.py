"""
Unit tests for ApertusClient, JSON parsing, and Decision Arbiter.
"""

import sys
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch

_pkg_root = Path(__file__).resolve().parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from src.apertus_client import ApertusClient, NLIOutput


class TestApertusClient(unittest.TestCase):
    def setUp(self):
        # Force mock mode for fast and deterministic unit testing
        self.client = ApertusClient(mock=True)

    def test_relation_prompt_is_opt_in_and_task_a_only(self):
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"label": 1, "evidence_ids": []}'))],
            usage=SimpleNamespace(prompt_tokens=20, completion_tokens=5, total_tokens=25),
        )
        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            return response, None

        self.client.mock = False
        with patch.object(self.client, "_create_with_retry", side_effect=create), \
                patch("src.config.A_RELATION_PROMPT", True):
            self.client.infer("same context", "same claim", passages=["same passage"], task_a=False)
            self.client.infer("same context", "same claim", passages=["same passage"], task_a=True)

        baseline_system, variant_system = [call["messages"][0]["content"] for call in calls]
        baseline_user, variant_user = [call["messages"][1]["content"] for call in calls]
        self.assertNotIn("RELATION CHECK", baseline_system)
        self.assertIn("RELATION CHECK", variant_system)
        self.assertEqual(baseline_user, variant_user)
        self.assertEqual(calls[0]["temperature"], calls[1]["temperature"])
        self.assertEqual(calls[0]["max_tokens"], calls[1]["max_tokens"])

    def test_skill_prompt_is_opt_in_and_task_a_only(self):
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"label": 1, "evidence_ids": []}'))],
            usage=SimpleNamespace(prompt_tokens=20, completion_tokens=5, total_tokens=25),
        )
        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            return response, None

        self.client.mock = False
        with patch.object(self.client, "_create_with_retry", side_effect=create):
            self.client.infer("ctx", "claim", passages=["passage"], task_a=True)  # switch off (default)
            with patch("src.config.A_SKILL_PROMPT", True):
                self.client.infer("ctx", "claim", passages=["passage"], task_a=False)  # not task A
                self.client.infer("ctx", "claim", passages=["passage"], task_a=True)

        off, not_a, on = [call["messages"][0]["content"] for call in calls]
        self.assertEqual(off, not_a)  # byte-identical without the skill
        self.assertNotIn("CLAIM CHECK", off)
        self.assertEqual(on, off + ApertusClient.A_SKILL_PROMPT_TEXT)  # only appended, nothing else changes
        self.assertEqual(len({call["messages"][1]["content"] for call in calls}), 1)
        self.assertEqual({(call["temperature"], call["max_tokens"]) for call in calls}, {(calls[0]["temperature"], calls[0]["max_tokens"])})

    def test_compact_prompt_is_opt_in_and_task_a_only(self):
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"label": 1, "evidence_ids": []}'))],
            usage=SimpleNamespace(prompt_tokens=20, completion_tokens=5, total_tokens=25),
        )
        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            return response, None

        self.client.mock = False
        with patch.object(self.client, "_create_with_retry", side_effect=create):
            self.client.infer("ctx", "claim", passages=["passage"], task_a=True)  # switch off (default)
            with patch("src.config.A_COMPACT_PROMPT", True):
                self.client.infer("ctx", "claim", passages=["passage"], task_a=False)  # not task A
                self.client.infer("ctx", "claim", passages=["passage"], task_a=True)

        off, not_a, on = [call["messages"][0]["content"] for call in calls]
        self.assertEqual(off, not_a)  # byte-identical without the compact rules
        self.assertNotIn("LABEL RULES", off)
        self.assertEqual(on, off + ApertusClient.A_COMPACT_PROMPT_TEXT)  # only appended, nothing else changes
        self.assertNotIn("CLAIM CHECK", on)  # not combined with the longer skill
        self.assertNotIn("RELATION CHECK", on)  # nor with the relation prompt
        self.assertEqual(len({call["messages"][1]["content"] for call in calls}), 1)
        self.assertEqual({(call["temperature"], call["max_tokens"]) for call in calls}, {(calls[0]["temperature"], calls[0]["max_tokens"])})

    def test_calibrated_decision_arbiter_conflict(self):
        # Rule 1: Conflict dominant
        label, rule = ApertusClient._apply_calibrated_decision(
            p_entail=0.10, p_neutral=0.20, p_contra=0.70, raw_label=0
        )
        self.assertEqual(label, 2)
        self.assertIn("Conflict dominant", rule)

    def test_calibrated_decision_keeps_label_when_confidences_disagree(self):
        # Rule 0: Apertus writes "label": 0 with "p_contra": 1.0 -> trust the label
        label, rule = ApertusClient._apply_calibrated_decision(
            p_entail=0.0, p_neutral=0.0, p_contra=1.0, raw_label=0, label_given=True
        )
        self.assertEqual(label, 0)
        self.assertIn("Decision-Rule 0", rule)

    def test_neutral_label_with_confident_relation_follows_confidences(self):
        # Rule 0b: "label": 1 with "p_contra": 1.0 is rarely Neutral
        label, rule = ApertusClient._apply_calibrated_decision(
            p_entail=0.0, p_neutral=0.0, p_contra=1.0, raw_label=1, label_given=True
        )
        self.assertEqual(label, 2)
        self.assertIn("Decision-Rule 0b", rule)

    def test_calibrated_decision_consistent_label_still_uses_rules(self):
        label, rule = ApertusClient._apply_calibrated_decision(
            p_entail=0.48, p_neutral=0.06, p_contra=0.46, raw_label=0, label_given=True
        )
        self.assertEqual(label, 1)
        self.assertIn("Epistemic ambiguity zone", rule)

    def test_calibrated_decision_arbiter_support(self):
        # Rule 2: Direct support dominant
        label, rule = ApertusClient._apply_calibrated_decision(
            p_entail=0.85, p_neutral=0.10, p_contra=0.05, raw_label=1
        )
        self.assertEqual(label, 0)
        self.assertIn("Direct support dominant", rule)

    def test_calibrated_decision_arbiter_neutrality(self):
        # Rule 3: High neutrality
        label, rule = ApertusClient._apply_calibrated_decision(
            p_entail=0.20, p_neutral=0.65, p_contra=0.15, raw_label=0
        )
        self.assertEqual(label, 1)
        self.assertIn("High neutrality", rule)

    def test_calibrated_decision_arbiter_ambiguity(self):
        # Rule 3: Epistemic ambiguity zone (|p_entail - p_contra| < 0.15)
        label, rule = ApertusClient._apply_calibrated_decision(
            p_entail=0.48, p_neutral=0.06, p_contra=0.46, raw_label=0
        )
        self.assertEqual(label, 1)
        self.assertIn("Epistemic ambiguity zone", rule)

    def test_backward_compatible_fuzzy_alias(self):
        label, rule = ApertusClient._apply_fuzzy_decision(
            p_entail=0.85, p_neutral=0.10, p_contra=0.05, raw_label=1
        )
        self.assertEqual(label, 0)

    def test_parse_json_clean(self):
        raw = '{"label": 0, "reasoning": "Supports statement", "evidence": ["Text sample"], "p_entail": 0.9}'
        parsed = ApertusClient._parse_json(raw)
        self.assertEqual(parsed["label"], 0)
        self.assertEqual(parsed["p_entail"], 0.9)

    def test_parse_json_markdown_blocks(self):
        raw = '```json\n{"label": 2, "reasoning": "Contradicts", "evidence": [], "p_contra": 0.8}\n```'
        parsed = ApertusClient._parse_json(raw)
        self.assertEqual(parsed["label"], 2)
        self.assertEqual(parsed["p_contra"], 0.8)

    def test_strip_thinking_keeps_only_the_final_answer(self):
        raw = '<|inner_prefix|>The committee says {"label": 2} is wrong.<|inner_suffix|>{"label": 0, "evidence_ids": [3]}'
        self.assertEqual(ApertusClient._parse_json(ApertusClient._strip_thinking(raw))["label"], 0)

    def test_strip_thinking_truncated_reasoning_uses_last_json(self):
        raw = '<|inner_prefix|>First guess {"label": 2}. On reflection {"label": 1, "p_neutral": 1.0}'
        self.assertEqual(ApertusClient._parse_json(ApertusClient._strip_thinking(raw))["label"], 1)
        self.assertEqual(ApertusClient._strip_thinking('{"label": 0}'), '{"label": 0}')

    def test_parse_json_embedded_fallback(self):
        raw = 'Here is the analysis result: {"label": 1, "reasoning": "Neutral topic"} Hope this helps!'
        parsed = ApertusClient._parse_json(raw)
        self.assertEqual(parsed["label"], 1)

    def test_mock_infer(self):
        context = "Die Volksinitiative verlangt, dass die ständige Wohnbevölkerung vor 2050 10 Millionen nicht überschreitet."
        claim = "Die Bevölkerung darf gemäss Initiative 10 Millionen Menschen nicht überschreiten."
        out = self.client.infer(context, claim, claim_language="de")

        self.assertIsInstance(out, NLIOutput)
        self.assertIn(out.label, (0, 1, 2))
        self.assertGreater(out.tokens_total, 0)
        self.assertGreater(out.latency_ms, 0.0)


# E7 (A_COMPACT_PROMPT). Request fingerprints (all request parameters except the environment-dependent model name)
# produced by the submission baseline 7c17c9c for fixed inputs: task A = infer() with passages, task B = verify_premise().
SUBMISSION_TASK_A_REQUESTS_SHA256 = "7229c1ce11d1250fd7ddabf53eb98f80daaf789fb3de19a58463f1f2fe18c465"
SUBMISSION_TASK_B_REQUESTS_SHA256 = "fe6bdd6bf7172e151b69f56db4cf65d898ba037ce31e967ba1546bbd6f2a2877"
# SHA-256 of the compact rules exactly as evaluated in E7 (runs E7_compact and the 180-case screen)
EVALUATED_COMPACT_PROMPT_SHA256 = "1d392f22b1eb19ee741f7a0fef1cd676c00ef05db480a811269abc8586d67adc"
# Prompt-relevant settings pinned to the submission defaults, so a developer .env cannot change the fingerprints
SUBMISSION_PROMPT_SETTINGS = {"THINKING": False, "PROMPT_SHORT": False, "IDS_REASON": False, "FEW_SHOT": False,
                              "TRANSLATE_CLAIM": False, "SPEAKER_HINT": False, "REFERENCE_MAX_CHARS": 6000}


class TestCompactPromptSwitch(unittest.TestCase):
    @staticmethod
    def _requests(task, **switches):
        import hashlib
        import json
        from contextlib import ExitStack
        from src.inference import ClaimVerificationEngine
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(
                content='{"label": 1, "evidence_ids": []}' if task == "A" else '{"label": 0, "evidence_ids": [1]}'))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2))
        client = ApertusClient(mock=True)
        client.mock = False
        calls = []
        settings = {**SUBMISSION_PROMPT_SETTINGS, "A_COMPACT_PROMPT": False, "A_SKILL_PROMPT": False,
                    "A_RELATION_PROMPT": False, **switches}
        with ExitStack() as stack:
            for name, value in settings.items():
                stack.enter_context(patch(f"src.config.{name}", value))
            stack.enter_context(patch.object(client, "_create_with_retry", side_effect=lambda **kw: (calls.append(kw), (response, None))[1]))
            if task == "A":
                client.infer("", "Si le vote est accepté, les droits de douane seront éliminés.", claim_language="fr",
                             passages=["(p. 9; Official explanation in detail) Die Zölle fallen weg.",
                                       "(p. 3) Abstimmungstext Art. 1"], task_a=True)
            else:
                ClaimVerificationEngine(apertus_client=client).verify_premise(
                    claim="Der Bundesrat empfiehlt die Ablehnung.", claim_language="de",
                    reference="Aus Sicht von Bundesrat und Parlament bringt die Initiative Unsicherheit. Empfehlung: Nein.",
                    case_id="b-1")
        payload = json.dumps([{k: v for k, v in c.items() if k != "model"} for c in calls], sort_keys=True, ensure_ascii=False)
        return calls, hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def test_switch_is_off_by_default(self):
        import os
        from tests.test_submission_config import effective_config
        clean = {k: v for k, v in os.environ.items() if k in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME")}
        defaults = effective_config(["A_COMPACT_PROMPT", "A_SKILL_PROMPT", "A_RELATION_PROMPT"], clean)
        self.assertEqual(defaults, {"A_COMPACT_PROMPT": False, "A_SKILL_PROMPT": False, "A_RELATION_PROMPT": False})

    def test_off_requests_are_byte_identical_to_the_submission_baseline(self):
        self.assertEqual(self._requests("A")[1], SUBMISSION_TASK_A_REQUESTS_SHA256)
        self.assertEqual(self._requests("B")[1], SUBMISSION_TASK_B_REQUESTS_SHA256)

    def test_task_b_requests_unchanged_with_every_task_a_switch_on(self):
        on = {"A_COMPACT_PROMPT": True, "A_SKILL_PROMPT": True, "A_RELATION_PROMPT": True}
        self.assertEqual(self._requests("B", **on)[1], SUBMISSION_TASK_B_REQUESTS_SHA256)

    def test_on_appends_exactly_the_evaluated_text_to_task_a_only(self):
        import hashlib
        self.assertEqual(hashlib.sha256(ApertusClient.A_COMPACT_PROMPT_TEXT.encode("utf-8")).hexdigest(),
                         EVALUATED_COMPACT_PROMPT_SHA256)
        off, _ = self._requests("A")
        on, digest = self._requests("A", A_COMPACT_PROMPT=True)
        self.assertNotEqual(digest, SUBMISSION_TASK_A_REQUESTS_SHA256)
        self.assertEqual(on[0]["messages"][0]["content"], off[0]["messages"][0]["content"] + ApertusClient.A_COMPACT_PROMPT_TEXT)
        self.assertEqual(on[0]["messages"][1:], off[0]["messages"][1:])  # user prompt (claim, passages) unchanged
        self.assertEqual({k: v for k, v in on[0].items() if k != "messages"}, {k: v for k, v in off[0].items() if k != "messages"})

    def test_compact_switch_enables_no_other_prompt_variant(self):
        on, _ = self._requests("A", A_COMPACT_PROMPT=True)
        system = on[0]["messages"][0]["content"]
        self.assertEqual(system.count("LABEL RULES"), 1)
        self.assertNotIn("CLAIM CHECK", system)  # A_SKILL_PROMPT
        self.assertNotIn("RELATION CHECK", system)  # A_RELATION_PROMPT


if __name__ == "__main__":
    unittest.main()
