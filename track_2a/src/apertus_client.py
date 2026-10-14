"""
Apertus Client for Natural Language Inference.
Interacts with Apertus v1.5 (8B / 70B) using the OpenAI-compatible CSCS endpoint.
Measures token consumption and inference latency.
"""

import time
import json
import logging
import math
import random
import re
import threading
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field

from src import config

logger = logging.getLogger(__name__)


class InFlightClock:
    """
    Time with at least one LLM request in flight, across threads. The official processing time is the wall clock
    minus exactly this, so wall clock minus `busy_s()` is our own estimate of the scored (non-LLM) time.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._active = 0
        self._since = 0.0
        self._busy = 0.0

    def __enter__(self):
        with self._lock:
            if self._active == 0:
                self._since = time.perf_counter()
            self._active += 1

    def __exit__(self, *exc):
        with self._lock:
            self._active -= 1
            if self._active == 0:
                self._busy += time.perf_counter() - self._since

    def busy_s(self) -> float:
        with self._lock:
            return self._busy + (time.perf_counter() - self._since if self._active else 0.0)


LLM_CLOCK = InFlightClock()

# Model the endpoint actually serves, if it refused the configured one (set at most once per run by _switch_model)
_MODEL_PREFERENCE = ("swiss-ai/Apertus-v1.5-70B-thinking", "swiss-ai/Apertus-v1.5-70B",
                     "swiss-ai/Apertus-v1.5-8B-thinking", "swiss-ai/Apertus-v1.5-8B")
_MODEL_SWITCH = {"tried": False, "model": None}
_MODEL_SWITCH_LOCK = threading.Lock()


def pick_model(ids: List[str], current: str) -> Optional[str]:
    """The best Apertus v1.5 model among the endpoint's model ids (preference order, then any v1.5), or None."""
    by_lower = {i.lower(): i for i in ids if isinstance(i, str)}
    for name in (current,) + _MODEL_PREFERENCE:
        if name.lower() in by_lower:
            return by_lower[name.lower()]
    v15 = sorted(i for i in by_lower.values() if "apertus-v1.5" in i.lower())
    return v15[0] if v15 else None


class NLIOutput(BaseModel):
    label: int = Field(..., description="0 = Entailment, 1 = Neutral, 2 = Contradiction")
    reasoning: str = Field(..., description="Short explanation of the relationship")
    evidence: List[str] = Field(default_factory=list, description="Exact supporting passage(s) from document")
    p_entail: float = Field(default=0.0, description="Calibrated confidence for Entailment [0..1]")
    p_neutral: float = Field(default=0.0, description="Calibrated confidence for Neutral [0..1]")
    p_contra: float = Field(default=0.0, description="Calibrated confidence for Contradiction [0..1]")
    fuzzy_rule_applied: Optional[str] = Field(default=None, description="Applied decision rule (alias)")
    decision_rule_applied: Optional[str] = Field(default=None, description="Applied calibrated decision rule")
    tokens_prompt: int = 0
    tokens_completion: int = 0
    tokens_total: int = 0
    latency_ms: float = 0.0
    error: Optional[str] = None
    evidence_ids: List[int] = Field(default_factory=list, description="1-based ids of cited passages (compact mode)")


class ApertusClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        mock: Optional[bool] = None,
    ):
        self.base_url = base_url or config.LLM_BASE_URL
        self.api_key = api_key if api_key is not None else config.LLM_API_KEY
        self.model_name = model_name or config.LLM_NAME
        self.mock = mock if mock is not None else (config.MOCK_APERTUS or not bool(self.api_key))

        if not self.mock:
            if not self.base_url or not self.api_key:
                raise ValueError("BASE_URL and API_KEY are required for remote Apertus inference")
            if "Apertus-v1.5" not in self.model_name:
                raise ValueError("Remote inference requires an Apertus v1.5 model")
            # Standard-library client instead of the openai SDK: same call, ~1 s less start-up (scored processing time);
            # retries are handled by _create_with_retry
            from src.http_chat import HTTPChatClient
            self.client = HTTPChatClient(base_url=self.base_url, api_key=self.api_key)
        else:
            self.client = None
            if not self.api_key:
                logger.info("No LLM_API_KEY provided; operating in local heuristic mock mode.")

    COMPACT_SYSTEM_PROMPT = (
        "You are a natural language inference (NLI) judge for official Swiss federal voting booklets.\n"
        "The passages and the claim may be in different languages (German, French, Italian): compare meaning, not wording.\n"
        "Decide how the PASSAGES relate to the CLAIM:\n"
        "0 = entailment: the passages support the claim.\n"
        "1 = neutral: the passages do not provide enough information to confirm or refute the claim "
        "(e.g. the detail, number, date or topic is not mentioned).\n"
        "2 = contradiction: the passages state something incompatible with the claim "
        "(e.g. a different number or date, the opposite recommendation, a negated statement).\n"
        "Judge only against the passages, never against world knowledge.\n"
        "Important: if the passages are about a different topic or simply do not address the specific statement of the claim, "
        "the answer is 1 (neutral), even if the claim sounds false. Choose 2 only when a passage explicitly states the opposite "
        "or a conflicting fact about the same subject.\n"
        "Answer format: the label digit, then '|', then the ids of the passages that justify the label, "
        "e.g. '0|P2' or '2|P3,P7'. For neutral answer '1|'. No other text."
    )

    # Task B prompts (E18): label only, no ids, no confidences. The rule order is the point: without a stated order
    # Apertus labels unrelated passages as contradiction (E13, E16). Written for this project.
    B_PROMPTS = {
        "topic": (
            "You check a CLAIM against REFERENCE passages from an official Swiss federal voting booklet. They may be "
            "in different languages (German, French, Italian): compare meaning, not wording. Use only the passages, "
            "never outside knowledge.\n"
            "Decide in this order:\n"
            "1. Do the passages deal with the subject of the claim (the same ballot and the same matter)? If not, "
            "the label is 1.\n"
            "2. If they do: 0 if they support the claim; 2 only if they state something that cannot be true "
            "together with the claim (a different number or date, the opposite recommendation); otherwise 1.\n"
            "Missing information is never a contradiction. 'According to the summary / the committee / the Federal "
            "Council, X' is 1 when that text does not say X.\n"
            "Labels: 0 entailment, 1 neutral, 2 contradiction. Answer with the digit only."
        ),
        "topic2": (
            "You check a CLAIM against REFERENCE passages from an official Swiss federal voting booklet. They may be "
            "in different languages (German, French, Italian): compare meaning, not wording. Use only the passages, "
            "never outside knowledge.\n"
            "Decide in this order:\n"
            "1. Do the passages deal with the subject of the claim (the same ballot and the same matter)? If not, "
            "the label is 1.\n"
            "2. If they do, compare what the claim asserts with what the passages say about that point: 0 if the "
            "passages say the same; 2 if they say the opposite or something incompatible (a negation, a reversed "
            "permission or condition, another number, date, name or recommendation); 1 only if the passages say "
            "nothing about that particular point.\n"
            "'According to the summary / the committee / the Federal Council, X' is 1 when that text does not say X.\n"
            "Labels: 0 entailment, 1 neutral, 2 contradiction. Answer with the digit only."
        ),
        "topic3": (
            "You check a CLAIM against REFERENCE passages from an official Swiss federal voting booklet. They may be "
            "in different languages (German, French, Italian): compare meaning, not wording. Use only the passages, "
            "never outside knowledge.\n"
            "Decide in this order:\n"
            "1. Do the passages deal with the subject of the claim (the same ballot and the same matter)? If not, "
            "the label is 1.\n"
            "2. If they do, compare what the claim asserts with what the passages say about that point: 0 if the "
            "passages say the same; 2 if they say the opposite or something incompatible (a negation, a reversed "
            "permission or condition, another number, date, name or recommendation); 1 only if the passages say "
            "nothing about that particular point.\n"
            "Do not choose 1 just because the claim is a negation or a restriction (no, not, only, never, any, "
            "all): check whether the passages say the opposite. A claim that merely adds a detail the passages do "
            "not mention is 1.\n"
            "Labels: 0 entailment, 1 neutral, 2 contradiction. Answer with the digit only."
        ),
        "topic4": (
            "You check a CLAIM against REFERENCE passages from an official Swiss federal voting booklet. They may be "
            "in different languages (German, French, Italian): compare meaning, not wording. Use only the passages, "
            "never outside knowledge.\n"
            "Decide in this order:\n"
            "1. Do the passages deal with the subject of the claim (the same ballot and the same matter)? If not, "
            "the label is 1.\n"
            "2. If they do, compare what the claim asserts with what the passages say about that point: 0 if the "
            "passages say the same; 2 if they say the opposite or something incompatible (a negation, a reversed "
            "permission or condition, another number, date, name or recommendation); 1 only if the passages say "
            "nothing about that particular point.\n"
            "Labels: 0 entailment, 1 neutral, 2 contradiction.\n"
            "Answer in one line: what the passages say about the claim in at most 12 words, then => and the label digit."
        ),
    }

    B_REASON_PROMPTS = {"topic4"}

    # E27: task A in the same order as the task B prompts, answered as '<label>|<ids>' (a few tokens instead of a
    # JSON object). Written for this project.
    _A_TOPIC = (
        "You check a CLAIM against numbered REFERENCE passages [P1], [P2], ... from an official Swiss federal voting "
        "booklet. They may be in different languages (German, French, Italian): compare meaning, not wording. Use "
        "only the passages, never outside knowledge.\n"
        "Decide in this order:\n"
        "1. Do the passages deal with the subject of the claim (the same ballot and the same matter)? If not, the "
        "label is 1.\n"
        "2. If they do: 0 if they support the claim; 2 only if they state something that cannot be true together "
        "with the claim (a different number or date, the opposite recommendation); otherwise 1.\n"
        "Missing information is never a contradiction. 'According to the summary / the committee / the Federal "
        "Council, X' is 1 when that text does not say X.\n"
        "Labels: 0 entailment, 1 neutral, 2 contradiction.\n")
    _A_ANSWER = ("Answer format: the label digit, then '|', then the ids of the passages that justify the label, "
                 "e.g. '0|P2' or '2|P3,P7'. For 1 answer '1|'. No other text.")

    def infer_label(
        self,
        passages: List[str],
        claim: str,
        claim_language: Optional[str] = None,
        prompt: str = "topic",
    ) -> NLIOutput:
        """Task B, label only: the short prompt B_PROMPTS[prompt], unnumbered passages, the label digit as the answer."""
        start_time = time.time()
        system_prompt = self.B_PROMPTS[prompt]
        reference = "\n\n".join(passages)
        lang = f" ({claim_language})" if claim_language else ""
        user_prompt = f"REFERENCE:\n{reference}\n\nCLAIM{lang}: {claim}\nLabel:"
        if self.mock:
            return self._mock_infer(reference, claim, 15.0)
        response, err = self._create_with_retry(
            model=self.model_name,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.0,
            max_tokens=48 if prompt in self.B_REASON_PROMPTS else 8,
            timeout=45.0,
            **({} if prompt in self.B_REASON_PROMPTS else {"logprobs": True, "top_logprobs": 5}),
        )
        if response is None and prompt not in self.B_REASON_PROMPTS:
            # an endpoint that refuses logprobs: the same request without them (the cascade then asks again)
            response, err = self._create_with_retry(
                model=self.model_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.0, max_tokens=8, timeout=45.0)
        latency_ms = round((time.time() - start_time) * 1000, 2)
        if response is None:
            return NLIOutput(label=1, reasoning=f"API Error: {err}", error=f"api: {err}", latency_ms=latency_ms)
        content = (response.choices[0].message.content or "").strip()
        probs = self._label_probs(response.choices[0])
        m = re.search(r"[012]", content)
        if prompt in self.B_REASON_PROMPTS:
            m = re.search(r"=>\s*([012])", content) or re.search(r"([012])\W*$", content)
            probs = {}
            if m and m.lastindex:
                m = re.match(r"([012])", m.group(1))
        if config.B_BIAS and len(config.B_BIAS) == 3 and len(probs) == 3 and all(v > 0 for v in probs.values()):
            label = max(probs, key=lambda k: math.log(probs[k]) + config.B_BIAS[k])
            m = re.match(r"(.)", str(label))
        if not m:
            return NLIOutput(label=1, reasoning=f"Unparseable answer: {content!r}", error=f"parse: {content!r}",
                             latency_ms=latency_ms)
        usage = getattr(response, "usage", None)
        tp = getattr(usage, "prompt_tokens", None) or self._estimate_tokens(system_prompt + user_prompt)
        tc = getattr(usage, "completion_tokens", None) or self._estimate_tokens(content)
        return NLIOutput(label=int(m.group(0)), reasoning=f"Apertus answer: {content}", tokens_prompt=tp,
                         tokens_completion=tc, tokens_total=tp + tc, latency_ms=latency_ms,
                         p_entail=probs.get(0, 0.0), p_neutral=probs.get(1, 0.0), p_contra=probs.get(2, 0.0))

    def infer_compact(
        self,
        passages: List[str],
        claim: str,
        claim_language: Optional[str] = None,
        vote: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> NLIOutput:
        """
        Token-efficient NLI: passages are numbered [P1]..[Pn]; the model answers '<label>|<ids>'.
        Label probabilities come from the logprobs of the first output token, and evidence is
        returned as passage ids, so quotes are always verbatim booklet text.
        """
        start_time = time.time()
        numbered = "\n\n".join(f"[P{i}] {txt}" for i, txt in enumerate(passages, 1))
        lang = f" ({claim_language})" if claim_language else ""
        vote_line = f"VOTE: {vote}\n" if vote else ""
        user_prompt = f"PASSAGES:\n{numbered}\n\n{vote_line}CLAIM{lang}: {claim}\nAnswer:"

        if self.mock:
            out = self._mock_infer("\n".join(passages), claim, 15.0)
            out.evidence_ids = [1] if out.label != 1 and passages else []
            return out

        response, err = self._chat(
            [{"role": "system", "content": system_prompt or self.COMPACT_SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
            max_tokens=24,
            logprobs=True,
        )
        latency_ms = round((time.time() - start_time) * 1000, 2)
        if response is None:
            return NLIOutput(label=1, reasoning=f"API Error: {err}", error=f"api: {err}", latency_ms=latency_ms)

        choice = response.choices[0]
        content = (choice.message.content or "").strip()
        m = re.match(r"\s*\**\s*([012])", content)
        probs = self._label_probs(choice)
        if m:
            label = int(m.group(1))
        elif probs:
            label = max(probs, key=probs.get)
        else:
            return NLIOutput(label=1, reasoning=f"Unparseable answer: {content!r}", error=f"parse: {content!r}", latency_ms=latency_ms)

        ids_part = content.split("|", 1)[1] if "|" in content else ""
        ids = []
        for tok in re.findall(r"\d+", ids_part):
            i = int(tok)
            if 1 <= i <= len(passages) and i not in ids:
                ids.append(i)

        usage = getattr(response, "usage", None)
        tp = getattr(usage, "prompt_tokens", None) or self._estimate_tokens((system_prompt or self.COMPACT_SYSTEM_PROMPT) + user_prompt)
        tc = getattr(usage, "completion_tokens", None) or self._estimate_tokens(content)
        return NLIOutput(
            label=label,
            reasoning=f"Apertus answer: {content}",
            evidence=[passages[i - 1] for i in ids],
            evidence_ids=ids,
            p_entail=probs.get(0, 0.0),
            p_neutral=probs.get(1, 0.0),
            p_contra=probs.get(2, 0.0),
            decision_rule="logprob argmax" if probs else None,
            tokens_prompt=tp,
            tokens_completion=tc,
            tokens_total=tp + tc,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _label_probs(choice) -> Dict[int, float]:
        """Normalised P(label) from the top logprobs of the first label-like output token."""
        lp = getattr(choice, "logprobs", None)
        if not lp or not lp.content:
            return {}
        for tok in lp.content[:3]:
            cands = {int(t.token.strip()): math.exp(t.logprob) for t in (tok.top_logprobs or []) if t.token.strip() in ("0", "1", "2")}
            if cands:
                total = sum(cands.values())
                return {k: round(v / total, 4) for k, v in cands.items()}
        return {}

    # Worked examples for the main error class: claims attributed to one side of the booklet.
    # Text from the 2026-06-14 booklet; the claims are written for this prompt (not taken from the dataset).
    FEW_SHOT_EXAMPLES = (
        "\n\nEXAMPLES (same passages for all three claims):\n"
        "[P1] (p. 16; Arguments of the initiative/referendum committee) Die ständige Wohnbevölkerung hat innerhalb "
        "von 12 Jahren um 1 Million Menschen zugenommen. Der Hauptgrund ist die massive Zuwanderung. "
        "Die Mieten werden immer teurer.\n"
        "[P2] (p. 18; Arguments of the Federal Council and Parliament) Die Initiative schadet dem Wohlstand. "
        "Schweizer Unternehmen sind auf ausländische Arbeitskräfte angewiesen. Die Wirtschaft und der Wohlstand "
        "der Schweiz würden leiden.\n"
        "CLAIM (fr): Selon le comité, l'immigration massive est la principale raison de la croissance démographique.\n"
        '{"p_entail": 1.0, "p_neutral": 0.0, "p_contra": 0.0, "label": 0, "evidence_ids": [1]}\n'
        "(The committee says this in P1. P2 argues against the initiative but does not contradict the committee's statement.)\n"
        "CLAIM (it): Secondo il comitato, la popolazione residente è diminuita negli ultimi dodici anni.\n"
        '{"p_entail": 0.0, "p_neutral": 0.0, "p_contra": 1.0, "label": 2, "evidence_ids": [1]}\n'
        "(The committee says the population grew by 1 million.)\n"
        "CLAIM (de): Der Bundesrat erwartet, dass die Initiative die Mieten in den Städten senkt.\n"
        '{"p_entail": 0.0, "p_neutral": 1.0, "p_contra": 0.0, "label": 1, "evidence_ids": []}\n'
        "(No passage says what the Federal Council expects for rents.)\n"
    )

    SHORT_SYSTEM_PROMPT = (
        "NLI over Swiss voting booklet passages [P1], [P2], ... and a CLAIM; languages may differ, compare meaning.\n"
        "0 Entailment: the passages directly support the claim.\n"
        "1 Neutral: the passages do NOT mention what the claim is about, or give too little information.\n"
        "2 Contradiction: the passages directly state the opposite (a different number, date or percentage is 2).\n"
        "- If the claim's topic is not mentioned in the passages, you MUST choose 1, never 2.\n"
        "- Claim attributes a statement to one side (Federal Council/Parliament vs. committee): judge only that "
        "side's text; the other side's arguments are no contradiction.\n"
        "- 'Recommends rejecting X' is 0 if they recommend No on X, 2 only if they recommend Yes.\n"
        "Give your confidence (0.0 to 1.0) for each relation, then the label. Respond ONLY with JSON:\n"
        '{"p_entail": <0.0 - 1.0>, "p_neutral": <0.0 - 1.0>, "p_contra": <0.0 - 1.0>, "label": <0, 1, or 2>, '
        '"evidence_ids": [<ids of the passages that justify the label, e.g. 2, 5; empty for 1>]}'
    )

    # Experiment (PROMPT_LEAN, 'ids' mode, both tasks): the rules of the full prompt in fewer words, same JSON schema
    # (with the "<0.0 - 1.0>" placeholders; written as 0-1 the confidences collapsed to 0 in the PROMPT_SHORT trial)
    LEAN_SYSTEM_PROMPT = (
        "You check a claim against numbered passages [P1], [P2], ... from an official Swiss voting booklet "
        "(Abstimmungsbüchlein). Passages and claim may be in different languages (German, French, Italian): compare "
        "meaning, not wording.\n\n"
        "Labels:\n"
        "- 0 Entailment: the passages directly support the claim.\n"
        "- 1 Neutral: the passages do NOT mention what the claim is about, or give too little information.\n"
        "- 2 Contradiction: the passages directly state the opposite of the claim.\n\n"
        "Rules:\n"
        "1. A number, date or percentage that differs from the passages (e.g. 500'000 vs 1.7 million, 2030 vs 2050) "
        "is a contradiction (2).\n"
        "2. If the claim's topic is not mentioned in the passages, you MUST choose 1 (Neutral), never 2.\n"
        "3. A claim that attributes a statement to an actor (the committee, the Federal Council, the summary) is "
        "judged only against that actor's text; the other side's arguments are not a contradiction.\n"
        "4. 'Recommends rejecting X' is 0 if the Federal Council and Parliament recommend No on X or reject X, 2 only "
        "if they recommend Yes.\n\n"
        "Estimate your confidence in each relation and respond ONLY with a valid JSON object:\n"
        "{\n"
        '  "p_entail": <0.0 - 1.0>,\n'
        '  "p_neutral": <0.0 - 1.0>,\n'
        '  "p_contra": <0.0 - 1.0>,\n'
        '  "label": <0, 1, or 2>,\n'
        '  "evidence_ids": [<ids of the passages that justify the label, e.g. 2, 5; empty for 1>]\n'
        "}"
    )

    LANGUAGE_NAMES = {"de": "German", "fr": "French", "it": "Italian"}

    def translate(self, text: str, target_lang: str) -> Tuple[Optional[str], int, int, float]:
        """Translate a claim into the booklet language. Returns (translation or None, prompt tokens, completion tokens, ms)."""
        start = time.time()
        if self.mock:
            return None, 0, 0, 0.0
        target = self.LANGUAGE_NAMES.get(target_lang, target_lang)
        response, _ = self._chat([
            {"role": "system", "content": f"Translate the user's sentence into {target}. Keep names, numbers and "
                                          "who says what exactly. Preserve negations and conditions; do not add or remove numerical values. Output only the translation."},
            {"role": "user", "content": text},
        ], max_tokens=200)
        ms = (time.time() - start) * 1000
        if response is None:
            return None, 0, 0, ms
        out = (response.choices[0].message.content or "").strip()
        usage = getattr(response, "usage", None)
        return (out or None, getattr(usage, "prompt_tokens", 0) or 0, getattr(usage, "completion_tokens", 0) or 0, ms)

    @staticmethod
    def _retry_limit(error: Exception) -> int:
        """
        How many retries an API error deserves. Timeouts, dropped connections, 429 and 5xx are transient.
        Under load the CSCS gateway also answers 'invalid API key' to valid keys (seen interleaved with successful
        calls; 403 likewise), so 401/403 get two quick retries, but not the full budget, so a really wrong key fails fast.
        Other client errors (400 bad request, 404 unknown model) are not retried.
        """
        status = getattr(error, "status_code", None)
        if status is None or status in (408, 409, 425, 429) or status >= 500:
            return config.LLM_MAX_RETRIES
        if status in (401, 403):
            return min(2, config.LLM_MAX_RETRIES)
        return 0

    def _create_with_retry(self, **kwargs) -> Tuple[Any, Optional[Exception]]:
        """chat.completions.create with exponential backoff (+ jitter) inside a per-request time budget."""
        # Output stays capped (max_tokens of the caller): output tokens are scored and a runaway answer would also
        # cost time. Per-call timeouts come from the caller; streaming is not used (no scoring benefit)
        json_output = kwargs.pop("_json_output", False)
        start = time.time()
        attempt = 0
        while True:
            try:
                return self._request_completion(**kwargs), None
            except Exception as e:
                status = getattr(e, "status_code", None)
                # CSCS answers an unknown model with an empty 403, like a refused key: after the quick 401/403 retries,
                # check the model list (a listed model or an unreadable list leaves the error as it is)
                if ((self._unknown_model(e) or (status in (401, 403) and attempt >= self._retry_limit(e)))
                        and self._switch_model(kwargs)):
                    continue  # same request with a model the endpoint serves (not counted as a retry)
                delay = min(30.0, 2.0 * 2 ** attempt) * random.uniform(0.5, 1.0)
                if attempt >= self._retry_limit(e) or time.time() - start + delay > config.LLM_RETRY_BUDGET_S:
                    logger.error("Apertus API failed after %s attempt(s): %s", attempt + 1, type(e).__name__)
                    status = getattr(e, "status_code", None)
                    if (config.LLM_JSON_REPAIR and json_output and
                            (status is None or status in (408, 429) or status >= 500)):
                        try:
                            # One explicit, separately counted generation attempt.
                            # The prompt, context, temperature and model stay fixed;
                            # only the supported JSON grammar constraint is added.
                            return self._request_completion(**{**kwargs, "response_format": {"type": "json_object"}}), None
                        except Exception as repair_error:
                            return None, repair_error
                    return None, e
                attempt += 1
                logger.warning("Apertus API attempt %s failed: %s; retry in %.1fs", attempt, type(e).__name__, delay)
                time.sleep(delay)

    @staticmethod
    def _unknown_model(error: Exception) -> bool:
        status = getattr(error, "status_code", None)
        return status == 404 or (status in (400, 422) and "model" in str(error).lower())

    def _switch_model(self, kwargs: Dict[str, Any]) -> bool:
        """
        The endpoint refused the model: read its /models list once per run and switch every later request to the best
        Apertus v1.5 model it serves. True if the request should be sent again with a different model.
        """
        with _MODEL_SWITCH_LOCK:
            if not _MODEL_SWITCH["tried"]:
                _MODEL_SWITCH["tried"] = True
                try:
                    listed = [m.get("id") for m in (self.client.get("/models") or {}).get("data", [])]
                except Exception as exc:
                    logger.error("Model %s refused and /models not readable (%s)", kwargs.get("model"), type(exc).__name__)
                    listed = []
                chosen = pick_model(listed, kwargs.get("model") or self.model_name)
                if chosen and chosen != kwargs.get("model"):
                    _MODEL_SWITCH["model"] = chosen
                    logger.warning("Model %s not served by the endpoint; using %s", kwargs.get("model"), chosen)
            chosen = _MODEL_SWITCH["model"]
        if chosen and chosen != kwargs.get("model"):
            kwargs["model"] = chosen
            self.model_name = chosen
            return True
        return False

    def _request_completion(self, **kwargs):
        """One remote attempt; LLM_CLOCK counts it as time with a request in flight (backoff stays outside)."""
        if _MODEL_SWITCH["model"]:
            kwargs["model"] = _MODEL_SWITCH["model"]
        with LLM_CLOCK:
            response = self.client.chat.completions.create(**kwargs)
        # 'length' is not an error here: a capped answer is still parsed (the label comes first), and repeating the
        # identical request would only return the same cut-off answer
        if getattr(response.choices[0], "finish_reason", None) == "content_filter":
            raise ValueError("Endpoint returned an incomplete completion")
        return response

    def _chat(self, messages: List[Dict[str, str]], max_tokens: int, logprobs: bool = False):
        kwargs = dict(model=self.model_name, messages=messages, temperature=0.0, max_tokens=max_tokens, timeout=60.0)
        if logprobs:
            kwargs.update(logprobs=True, top_logprobs=5)
        return self._create_with_retry(**kwargs)

    # Prompt-screening variant (A_SKILL_PROMPT, task A only): structure the claim, then a label rule that also
    # guards against reading a paraphrase or summary as a contradiction (the largest task A error class)
    A_SKILL_PROMPT_TEXT = (
        "\nCLAIM CHECK (do this before choosing the label):\n"
        "1. Parse the claim into actor or affected group, action or state, object, and qualifiers: numbers, units, "
        "time, conditions, exceptions, cause vs. mere sequence, modality (must / may / will / should). Add nothing "
        "the claim does not say.\n"
        "2. Find the passage(s) on the same actor and object; combine passages when the claim needs several. Use "
        "only these passages.\n"
        "3. 0 if the passages state every part, also when worded differently, summarised, or in another language. "
        "2 only if they state something incompatible about the same point: the opposite, another value, another "
        "actor, another modality (may vs. must). 1 if a part is not settled by the passages. Missing support is "
        "never 2; an explicit conflict is never 1.\n"
        "evidence_ids: the passages that contain the deciding statement.\n"
    )
    # Prompt-screening variant (A_COMPACT_PROMPT, task A only): the label rules of the skill in a few lines
    A_COMPACT_PROMPT_TEXT = (
        "\nLABEL RULES: Compare actor, action, object and the decisive conditions or modality of the claim with the "
        "passages. 0 only if the passages support the claim, also when worded differently, summarised or in another "
        "language, but never on information they do not state. 2 only if they state something incompatible with the "
        "same claim; missing support is not a contradiction. 1 if they neither support nor refute it. Use only the "
        "passages, no outside facts.\n"
    )
    A_PROMPTS = {"topic": _A_TOPIC + _A_ANSWER,
                 "topic_rules": _A_TOPIC + A_COMPACT_PROMPT_TEXT.lstrip("\n") + _A_ANSWER}

    # E25: blocks of the 'ids' system prompt that task A can leave out (A_PROMPT_DROP); each is removed verbatim
    _CONFIDENCE_HELP = (
        "3. CONTINUOUS CONFIDENCE: Estimate fuzzy membership degrees [0.0 to 1.0] for:\n"
        "   - p_entail: confidence of direct textual support\n"
        "   - p_neutral: confidence of missing/unaddressed information\n"
        "   - p_contra: confidence of factual, numerical, or logical contradiction\n\n")
    A_PROMPT_BLOCKS = {
        "role": ["You are an expert multilingual document-grounded Natural Language Inference (NLI) system "
                 "for official Swiss voting booklets (Abstimmungsbüchlein).\n"],
        "classes": ["Classification Rules:\n"
                    "- 0: Entailment -> The document context directly supports or confirms the claim.\n"
                    "- 1: Neutral -> The document context does NOT mention the claim, or contains insufficient information.\n"
                    "- 2: Contradiction -> The document context directly contradicts, refutes, or states the opposite of the claim.\n\n"],
        "numbers": ["1. NUMBERS, QUANTITIES & DATES: If a claim cites a number, date, or percentage that differs from the "
                    "document (e.g. 500'000 vs 1.7 million, or 2030 vs 2050), it is a DIRECT CONTRADICTION (2)!\n"],
        "unmentioned": ["2. UNMENTIONED TOPICS: If a claim is about a topic not mentioned in the text, you MUST choose 1 "
                        "(Neutral), never 2.\n"],
        "confidence": [_CONFIDENCE_HELP],
        # no confidences at all: shorter answer; the decision rules then keep the model's label
        "probs": [_CONFIDENCE_HELP, '  "p_entail": <0.0 - 1.0>,\n  "p_neutral": <0.0 - 1.0>,\n  "p_contra": <0.0 - 1.0>,\n'],
    }

    def infer(
        self,
        context: str,
        claim: str,
        claim_language: Optional[str] = None,
        passages: Optional[List[str]] = None,
        task_a: bool = False,
        label_only: bool = False,
    ) -> NLIOutput:
        """
        Evaluate whether the booklet context entails, contradicts, or is neutral towards the claim.
        Returns NLIOutput with label (0, 1, 2), reasoning, evidence, tokens, and latency.

        If `passages` is given ('ids' mode), they are numbered [P1]..[Pn] and replace `context`;
        the model cites passage ids instead of writing quotes and reasoning (far fewer output tokens).
        """
        start_time = time.time()
        if passages is not None:
            context = "\n\n".join(f"[P{i}] {txt}" for i, txt in enumerate(passages, 1))

        if self.mock:
            # Deterministic heuristic mock for offline development and testing
            latency_ms = (time.time() - start_time) * 1000 + 15.0
            return self._mock_infer(context, claim, latency_ms)

        system_prompt = (
            "You are an expert multilingual document-grounded Natural Language Inference (NLI) system "
            "for official Swiss voting booklets (Abstimmungsbüchlein).\n"
            "Evaluate the logical relationship between the document context and the given claim.\n\n"
            "Classification Rules:\n"
            "- 0: Entailment -> The document context directly supports or confirms the claim.\n"
            "- 1: Neutral -> The document context does NOT mention the claim, or contains insufficient information.\n"
            "- 2: Contradiction -> The document context directly contradicts, refutes, or states the opposite of the claim.\n\n"
            "CRITICAL CHECKLIST:\n"
            "1. NUMBERS, QUANTITIES & DATES: If a claim cites a number, date, or percentage that differs from the document (e.g. 500'000 vs 1.7 million, or 2030 vs 2050), it is a DIRECT CONTRADICTION (2)!\n"
            "2. UNMENTIONED TOPICS: If a claim is about a topic not mentioned in the text, you MUST choose 1 (Neutral), never 2.\n"
            "2b. VIEWPOINTS: The booklet deliberately contains opposing viewpoints (Federal Council and Parliament vs. the "
            "initiative or referendum committee). If the claim attributes a statement to an actor (e.g. 'the committee argues...', "
            "'the Federal Council recommends...', 'according to the summary...'), check only whether THAT actor's text supports it. "
            "Arguments of the other side are NOT a contradiction.\n"
            "2c. RECOMMENDATIONS: 'recommends rejecting X' is supported (0) by text where the Federal Council/Parliament recommend "
            "'No' on X or reject X; it is contradicted (2) only if they recommend 'Yes'.\n"
            "3. CONTINUOUS CONFIDENCE: Estimate fuzzy membership degrees [0.0 to 1.0] for:\n"
            "   - p_entail: confidence of direct textual support\n"
            "   - p_neutral: confidence of missing/unaddressed information\n"
            "   - p_contra: confidence of factual, numerical, or logical contradiction\n\n"
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "p_entail": <0.0 - 1.0>,\n'
            '  "p_neutral": <0.0 - 1.0>,\n'
            '  "p_contra": <0.0 - 1.0>,\n'
            '  "label": <0, 1, or 2>,\n'
            '  "reasoning": "<concise explanation in the claim language>",\n'
            '  "evidence": ["<verbatim supporting quote or passage from the document>"]\n'
            "}"
        )
        if passages is not None and config.FEW_SHOT:
            system_prompt = system_prompt + self.FEW_SHOT_EXAMPLES
        if passages is not None and config.IDS_REASON:
            system_prompt = system_prompt.replace(
                '{\n  "p_entail"',
                '{\n  "reason": "<max. 15 words: what the most relevant passage says about the claim>",\n  "p_entail"',
            )
        if passages is not None:
            system_prompt = system_prompt.replace(
                '  "reasoning": "<concise explanation in the claim language>",\n'
                '  "evidence": ["<verbatim supporting quote or passage from the document>"]\n',
                '  "evidence_ids": [<ids of the passages that justify the label, e.g. 2, 5; empty for 1>]\n',
            ).replace(
                "Evaluate the logical relationship between the document context and the given claim.\n",
                "Evaluate the logical relationship between the document context and the given claim. "
                "The context is a list of numbered passages [P1], [P2], ... and may be in a different "
                "language (German, French, Italian) than the claim: compare meaning, not wording.\n",
            )

        if label_only and passages is not None:
            # B_LABEL_ONLY (task B, whose evidence is not scored): the same prompt asking for the label alone
            system_prompt = system_prompt.replace(
                "3. CONTINUOUS CONFIDENCE: Estimate fuzzy membership degrees [0.0 to 1.0] for:\n"
                "   - p_entail: confidence of direct textual support\n"
                "   - p_neutral: confidence of missing/unaddressed information\n"
                "   - p_contra: confidence of factual, numerical, or logical contradiction\n\n", "\n").replace(
                '{\n  "p_entail": <0.0 - 1.0>,\n  "p_neutral": <0.0 - 1.0>,\n  "p_contra": <0.0 - 1.0>,\n'
                '  "label": <0, 1, or 2>,\n'
                '  "evidence_ids": [<ids of the passages that justify the label, e.g. 2, 5; empty for 1>]\n}',
                '{"label": <0, 1, or 2>}')

        if passages is not None and config.PROMPT_LEAN:
            system_prompt = self.LEAN_SYSTEM_PROMPT

        if task_a and passages is not None and config.A_RELATION_PROMPT:
            system_prompt += (
                "\nRELATION CHECK (apply before choosing the label): Compare the same proposition across the claim "
                "and the passages: who is involved, what action or state and object are asserted, and the relevant "
                "properties, including negation, amount and unit, time, scope, conditions, and modality. Label 0 "
                "when a passage states the same fact or a logically equivalent one. Label 2 only when the text "
                "states an incompatible fact about that same actor, action, object, and property (for example an "
                "explicit opposite, negation, or conflicting value). A missing detail, silence, or an unsupported "
                "claim is not a contradiction; use 1 when the passages do not settle it. Do not turn an explicit "
                "opposite or conflicting value into Neutral. A different speaker's position is not a contradiction "
                "of the attributed speaker's claim.\n"
            )
        if task_a and passages is not None and config.A_SKILL_PROMPT:
            system_prompt += self.A_SKILL_PROMPT_TEXT
        if task_a and passages is not None and config.A_COMPACT_PROMPT:
            system_prompt += self.A_COMPACT_PROMPT_TEXT
        if task_a and passages is not None and config.A_PROMPT_DROP:
            for name in [b.strip() for b in config.A_PROMPT_DROP.split(",") if b.strip()]:
                for text in self.A_PROMPT_BLOCKS[name]:
                    if text not in system_prompt:
                        raise ValueError(f"A_PROMPT_DROP={name}: block not in the task A prompt")
                    system_prompt = system_prompt.replace(text, "")

        if passages is not None and config.PROMPT_SHORT:
            # Same rules in fewer words: input tokens are scored relative to the most frugal team
            system_prompt = self.SHORT_SYSTEM_PROMPT

        thinking = passages is not None and config.THINKING
        if thinking:
            system_prompt = system_prompt.replace(
                "Respond ONLY with a valid JSON object matching this schema:\n",
                "First think briefly (at most 120 words): who (if anyone) the claim attributes the statement to, "
                "which passages belong to that speaker, and what exactly they say about the claim. Then give your "
                "final answer as a valid JSON object matching this schema:\n",
            )

        # Kept in the short prompt too: without the closing question Apertus labels unrelated passages as contradiction
        user_prompt = (
            f"=== DOCUMENT CONTEXT ===\n{context}\n\n"
            f"=== CLAIM ===\n{claim}\n\n"
            "Determine whether the document context entails (0), is neutral (1), or contradicts (2) the claim. "
            + ("Think it through, then output the JSON:" if thinking else "Output JSON only:")
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        extra: Dict[str, Any] = {}
        if thinking:
            # Asked to think, Apertus still answers with the JSON first and explains afterwards; prefilling the
            # reasoning marker makes it reason before deciding
            messages.append({"role": "assistant", "content": "<|inner_prefix|>"})
            extra["extra_body"] = {"continue_final_message": True, "add_generation_prompt": False}

        budget = 0  # no forced second answer: thinking is capped by THINKING_MAX_TOKENS only (and off by default)
        response, last_exception = self._create_with_retry(
            _json_output=True,
            model=self.model_name,
            messages=messages,
            temperature=0.0,
            max_tokens=(budget or config.THINKING_MAX_TOKENS) if thinking else (512 if passages is None else 160),
            timeout=180.0 if thinking else 45.0,
            **extra,
        )

        forced_prompt = forced_completion = 0

        if response is None:
            latency_ms = (time.time() - start_time) * 1000
            return NLIOutput(
                label=1,
                reasoning=f"API Error: {str(last_exception)}",
                evidence=[],
                error=f"api: {last_exception}",
                tokens_prompt=0,
                tokens_completion=0,
                tokens_total=0,
                latency_ms=round(latency_ms, 2),
            )

        try:
            latency_ms = (time.time() - start_time) * 1000
            content = response.choices[0].message.content.strip()
            parsed_json = self._parse_json(self._strip_thinking(content, thinking=thinking))

            usage = getattr(response, "usage", None)
            tokens_prompt = usage.prompt_tokens if (usage and getattr(usage, "prompt_tokens", None)) else self._estimate_tokens(user_prompt)
            tokens_completion = usage.completion_tokens if (usage and getattr(usage, "completion_tokens", None)) else self._estimate_tokens(content)
            tokens_total = usage.total_tokens if (usage and getattr(usage, "total_tokens", None)) else (tokens_prompt + tokens_completion)
            tokens_prompt += forced_prompt
            tokens_completion += forced_completion
            tokens_total += forced_prompt + forced_completion

            label_given = "label" in parsed_json
            raw_label = int(parsed_json.get("label", 1))
            if raw_label not in (0, 1, 2):
                raw_label, label_given = 1, False

            p_entail = float(parsed_json.get("p_entail", 0.0))
            p_neutral = float(parsed_json.get("p_neutral", 0.0))
            p_contra = float(parsed_json.get("p_contra", 0.0))

            # Apply Calibrated Decision Arbiter
            final_label, decision_rule = self._apply_calibrated_decision(
                p_entail, p_neutral, p_contra, raw_label, label_given=label_given)

            evidence = parsed_json.get("evidence", [])
            if isinstance(evidence, str):
                evidence = [evidence]

            evidence_ids: List[int] = []
            if passages is not None:
                raw_ids = parsed_json.get("evidence_ids", [])
                for tok in re.findall(r"\d+", json.dumps(raw_ids)):
                    i = int(tok)
                    if 1 <= i <= len(passages) and i not in evidence_ids:
                        evidence_ids.append(i)
                evidence = [passages[i - 1] for i in evidence_ids]

            return NLIOutput(
                label=final_label,
                reasoning=parsed_json.get("reasoning", "") or f"Apertus answer: {content}",
                evidence=evidence,
                evidence_ids=evidence_ids,
                p_entail=p_entail,
                p_neutral=p_neutral,
                p_contra=p_contra,
                fuzzy_rule_applied=decision_rule,
                decision_rule_applied=decision_rule,
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                tokens_total=tokens_total,
                latency_ms=round(latency_ms, 2),
            )
        except Exception as e:
            logger.error(f"Error parsing Apertus response: {e}")
            latency_ms = (time.time() - start_time) * 1000
            return NLIOutput(
                label=1,
                reasoning=f"Response Parse Error: {str(e)}",
                evidence=[],
                error=f"parse: {e}",
                tokens_prompt=0,
                tokens_completion=0,
                tokens_total=0,
                latency_ms=round(latency_ms, 2),
            )

    @classmethod
    def _apply_fuzzy_decision(cls, p_entail: float, p_neutral: float, p_contra: float, raw_label: int) -> Tuple[int, Optional[str]]:
        """Backward-compatible alias for _apply_calibrated_decision."""
        return cls._apply_calibrated_decision(p_entail, p_neutral, p_contra, raw_label)

    @staticmethod
    def _apply_calibrated_decision(
        p_entail: float, p_neutral: float, p_contra: float, raw_label: int, label_given: bool = False,
    ) -> Tuple[int, Optional[str]]:
        """
        Calibrated decision arbiter:
        Applies empirical threshold rules over the model's confidence distribution
        [p_entail, p_neutral, p_contra] to resolve epistemic ambiguity and numerical conflicts.
        """
        total_p = p_entail + p_neutral + p_contra
        if total_p == 0.0:
            return raw_label, None

        # Rule 0: a self-inconsistent answer ("label": 0 with "p_contra": 1.0) keeps the model's label.
        # Over all saved ids-mode runs the label was right in 44 of these cases and the probabilities in 13.
        probs = (p_entail, p_neutral, p_contra)
        if label_given and probs[raw_label] < max(probs):
            # Rule 0b: except "label": 1 (Neutral) with the confidence on Entailment/Contradiction. That answer was
            # right in 1 of 18 such cases over all 1,495 OST pairs; the confidences' choice fixed 8 and broke 1
            if raw_label == 1:
                return probs.index(max(probs)), "Decision-Rule 0b: Neutral label but confidences name a relation -> confidences"
            return raw_label, "Decision-Rule 0: label and confidences disagree -> model label kept"

        # Rule 1: Strong contradiction or numerical conflict signal
        if p_contra >= 0.40 and p_contra > p_entail:
            return 2, "Decision-Rule 1: Conflict dominant (p_contra >= 0.40)"

        # Rule 2: Strong direct support
        if p_entail >= 0.60 and p_contra < 0.25:
            return 0, "Decision-Rule 2: Direct support dominant (p_entail >= 0.60)"

        # Rule 3: High neutral probability or genuine ambiguity between entail and contra
        if p_neutral >= 0.40:
            return 1, "Decision-Rule 3: High neutrality (p_neutral >= 0.40)"
        if (p_entail > 0.0 or p_contra > 0.0) and abs(p_entail - p_contra) < 0.15:
            return 1, "Decision-Rule 3: Epistemic ambiguity zone (|p_entail - p_contra| < 0.15)"

        return raw_label, None

    @staticmethod
    def _strip_thinking(text: str, thinking: bool = False) -> str:
        """
        The thinking model writes '<|inner_prefix|>reasoning<|inner_suffix|>answer'. Return only the answer;
        if the reasoning was cut off before the suffix, fall back to the last JSON object that has a label.
        """
        if "<|inner_suffix|>" in text:
            return text.rsplit("<|inner_suffix|>", 1)[1].strip()
        if thinking or "<|inner_prefix|>" in text:
            objects = re.findall(r"\{[^{}]*\"label\"[^{}]*\}", text)
            return objects[-1] if objects else text
        return text

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        text = text.strip()
        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            return json.loads(text, strict=False)
        except Exception:
            # Fallback search for JSON object inside braces
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start : end + 1], strict=False)
                except Exception:
                    pass
            
            # Regex fallback
            import re
            label_match = re.search(r'"label"\s*:\s*([012])', text)
            p_entail_match = re.search(r'"p_entail"\s*:\s*([0-9.]+)', text)
            p_neutral_match = re.search(r'"p_neutral"\s*:\s*([0-9.]+)', text)
            p_contra_match = re.search(r'"p_contra"\s*:\s*([0-9.]+)', text)
            
            ids_match = re.search(r'"evidence_ids"\s*:\s*\[([^\]]*)\]', text)
            if label_match:
                return {
                    "evidence_ids": re.findall(r"\d+", ids_match.group(1)) if ids_match else [],
                    "label": int(label_match.group(1)),
                    "p_entail": float(p_entail_match.group(1)) if p_entail_match else 0.0,
                    "p_neutral": float(p_neutral_match.group(1)) if p_neutral_match else 0.0,
                    "p_contra": float(p_contra_match.group(1)) if p_contra_match else 0.0,
                    "reasoning": "Parsed via regex fallback",
                    "evidence": []
                }
            return {"label": 1, "reasoning": "Could not parse model response as JSON", "evidence": []}

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        Multilingual token estimation for Swiss languages (DE, FR, IT).
        Empirically calibrated to Apertus/Llama tokenizers: ~3.7 characters per token.
        """
        if not text:
            return 0
        return max(1, int(len(text) / 3.7))

    def _mock_infer(self, context: str, claim: str, latency_ms: float) -> NLIOutput:
        """
        Mock inference for offline testing.
        Uses lexical overlap heuristics to generate a plausible response.
        """
        prompt_est = self._estimate_tokens(context) + self._estimate_tokens(claim) + 50
        comp_est = 45

        # Heuristic: check if claim words appear in context
        claim_words = [w.lower() for w in claim.split() if len(w) > 4]
        match_count = sum(1 for w in claim_words if w in context.lower())

        if not claim_words or match_count == 0:
            label = 1  # Neutral
            reasoning = "Das offizielle Abstimmungsbüchlein enthält zu dieser Fragestellung keine definitive Aussage."
            evidence = []
        elif "nicht" in claim.lower() or "kein" in claim.lower() or "500'000" in claim:
            label = 2  # Contradiction
            reasoning = "Die Behauptung steht im Widerspruch zu den offiziellen Zahlen oder Empfehlungen im Abstimmungsbüchlein."
            evidence = [context[:200]]
        else:
            label = 0  # Entailment
            reasoning = "Die Kernaussage wird durch die amtlichen Ausführungen des Abstimmungsbüchleins gestützt und bestätigt."
            evidence = [context[:200]]

        return NLIOutput(
            label=label,
            reasoning=reasoning,
            evidence=evidence,
            tokens_prompt=prompt_est,
            tokens_completion=comp_est,
            tokens_total=prompt_est + comp_est,
            latency_ms=round(latency_ms, 2),
        )
