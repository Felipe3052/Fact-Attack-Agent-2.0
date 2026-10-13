"""
Configuration and Environment Management for Hack Apertus Track 2A (OST).
"""

import os
from pathlib import Path
import tempfile
from dotenv import load_dotenv

_RUNTIME_LLM_ENV = {name: os.environ[name] for name in
                    ("BASE_URL", "API_KEY", "LLM_BASE_URL", "LLM_API_KEY") if name in os.environ}

# Search for .env in track_2a directory or repo root
BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

if (BASE_DIR / ".env").exists():
    load_dotenv(BASE_DIR / ".env")
elif (REPO_ROOT / ".env").exists():
    load_dotenv(REPO_ROOT / ".env")
else:
    load_dotenv()

# Apertus / LLM Endpoint Config. The official evaluation injects BASE_URL (its token-counting proxy) and API_KEY;
# they take precedence over the older LLM_* names, so no call can bypass the proxy
# MODEL is accepted as an alias (some setups name the model that way); if the endpoint does not serve this model, the
# client switches once to the best Apertus v1.5 model it lists (src/apertus_client.py, _switch_model)
LLM_NAME = os.getenv("LLM_NAME") or os.getenv("MODEL") or "swiss-ai/Apertus-v1.5-70B-thinking"
def _endpoint_setting(official, legacy):
    # Any runtime setting outranks a .env value, including across alias names.
    for name in (official, legacy):
        if name in _RUNTIME_LLM_ENV:
            return _RUNTIME_LLM_ENV[name]
    return os.getenv(official) or os.getenv(legacy) or ""


LLM_BASE_URL = _endpoint_setting("BASE_URL", "LLM_BASE_URL") or "https://api.inference.cscs.ch/v1"
LLM_API_KEY = _endpoint_setting("API_KEY", "LLM_API_KEY")
# Kept for the measurement scripts; the submission does not stream (no scoring benefit) and uses per-call timeouts
LLM_STREAMING = os.getenv("LLM_STREAMING", "false").lower() in ("true", "1", "yes")
LLM_REQUEST_TIMEOUT_S = float(os.getenv("LLM_REQUEST_TIMEOUT_S", "600"))
# After the retries of an NLI request failed: one last attempt with the JSON grammar constraint instead of a neutral
# answer. Only on that failure path (free JSON stays the default: a schema on every call cost 0.10 macro-F1)
LLM_JSON_REPAIR = os.getenv("LLM_JSON_REPAIR", "true").lower() in ("true", "1", "yes")
OFFICIAL_IO = os.getenv("NLI_OFFICIAL_IO", "false").lower() in ("true", "1", "yes")

# Retries on transient API errors (timeouts, 429, 5xx): exponential backoff within a time budget per request.
# A failed request would otherwise silently count as Neutral
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "6"))
LLM_RETRY_BUDGET_S = float(os.getenv("LLM_RETRY_BUDGET_S", "120"))

# Context strategy: 'hybrid' (booklet-wide BM25 claim + vote title), 'retrieval' (proposal filter + BM25) or 'full'
DEFAULT_STRATEGY = os.getenv("NLI_STRATEGY", "hybrid")
# 8 pages: on 300 dev cases (official evaluate.py) k=12 / 10 / 8 / 7 / 6 give macro-F1 0.937 / 0.934 / 0.934 / 0.924 / 0.904,
# Hit@5 0.70 / 0.70 / 0.76 / 0.72 / 0.72 and 5,370 / 4,495 / 3,721 / 3,360 / 3,023 input tokens: tokens are scored
# relative to the most frugal team, so k=8 trades -0.003 F1 for 31 % fewer tokens
DEFAULT_TOP_K = int(os.getenv("NLI_TOP_K", "8"))
# Max characters per booklet passage; 0 = whole pages (default: on dev, n=450, pages scored 0.908 F1 vs 0.831 for 600-char passages)
PASSAGE_CHARS = int(os.getenv("PASSAGE_CHARS", "0"))

# Max characters per retrieved page sent to the model (0 = no limit). Longer pages keep the window of
# sentences that best matches claim + vote title; only a few dense legal-text pages are affected.
# 3000: test input tokens 5,725 -> 4,696 (p95 12.7k -> 7.4k), macro-F1 0.925 -> 0.928 (dev 0.908 -> 0.913)
PAGE_MAX_CHARS = int(os.getenv("PAGE_MAX_CHARS", "3000"))
# Experiment (task A): a smaller window for the lower-ranked context pages only. Pages after the first PAGE_FULL_RANKS
# keep at most PAGE_MAX_CHARS_TAIL characters (0 = off). The best gold page is among the first 4 in 85 % of the cases.
PAGE_MAX_CHARS_TAIL = int(os.getenv("PAGE_MAX_CHARS_TAIL", "0"))
PAGE_FULL_RANKS = int(os.getenv("PAGE_FULL_RANKS", "4"))
# E12 (adopted): contents-guided part selection (task A): the context is the booklet part the claim's opening names (summary,
# detail, committee, Federal Council, voting text) of the case's vote, located with the booklet's contents page
# (src/part_context.py); at most PART_CONTEXT_CHARS characters, best-matching pages first. Claims without a part use the
# regular retrieval.
PART_CONTEXT = os.getenv("PART_CONTEXT", "true").lower() in ("true", "1", "yes")
PART_CONTEXT_CHARS = int(os.getenv("PART_CONTEXT_CHARS", "6000"))
# Processing time: a booklet that is not parsed yet is read page by page for the first cases' parts (contents page,
# headings, the part's pages; src/quick_booklet.py), the same text and evidence, while the full parse goes on
QUICK_PARTS = os.getenv("QUICK_PARTS", "true").lower() in ("true", "1", "yes")
# Experiment (task B): ask for the label only, without confidences and passage ids (task B evidence is not scored)
B_LABEL_ONLY = os.getenv("B_LABEL_ONLY", "false").lower() in ("true", "1", "yes")
# Task B (experiment E18): name of a short label-only prompt in ApertusClient.B_PROMPTS ("" = the full prompt of 'ids'
# mode). The answer is the label digit alone and the passages are sent unnumbered, because task B's evidence is not scored.
B_PROMPT = os.getenv("B_PROMPT", "topic").strip()
# Task B label-only prompt: log-space bias added to the label probabilities (labels 0,1,2) before the argmax, e.g.
# "0,0.5,0"; empty = the model's own label. B_PROBS_JOURNAL_PATH: one JSON line per case with the probabilities.
B_BIAS = [float(v) for v in os.getenv("B_BIAS", "").split(",") if v.strip()]
B_PROBS_JOURNAL_PATH = os.getenv("B_PROBS_JOURNAL_PATH", "").strip()
# Task B cascade (E19): when the label-only answer's top probability is below this value (or unreadable), the case is
# asked again with the full prompt of 'ids' mode and that answer counts (0 = no second call). Both calls' tokens count.
B_ESCALATE_BELOW = float(os.getenv("B_ESCALATE_BELOW", "0.98"))
# Task B cascade: characters of the reference the first (label-only) call sees; the second call keeps the full budget
# (0 = the same passages in both calls). A cut reference makes the first answer less sure, so more cases escalate.
B_SHORT_CHARS = int(os.getenv("B_SHORT_CHARS", "2000"))
# Experiment (both tasks, 'ids' mode): the system prompt's rules in fewer words (ApertusClient.LEAN_SYSTEM_PROMPT)
PROMPT_LEAN = os.getenv("PROMPT_LEAN", "false").lower() in ("true", "1", "yes")

# Prompt mode:
#   'ids'     - JSON with confidences + cited passage ids (default: best F1, ~55 output tokens)
#   'json'    - JSON with reasoning + verbatim quotes (~150 output tokens)
#   'compact' - label digit + ids with logprob confidences (fewest tokens, weaker on Neutral)
PROMPT_MODE = os.getenv("PROMPT_MODE", "ids")

# 'ids' mode: let the model write one short sentence before its confidences (a minimal reasoning step)
IDS_REASON = os.getenv("IDS_REASON", "false").lower() in ("true", "1", "yes")

# Prompt-screening switch: add the contrastive entity/action/property checklist to Task A only.
# Disabled by default; it changes no submission behaviour unless explicitly enabled.
A_RELATION_PROMPT = os.getenv("A_RELATION_PROMPT", "false").lower() in ("true", "1", "yes")
# Prompt-screening switch: the compact claim-check skill, Task A only. Disabled by default.
A_SKILL_PROMPT = os.getenv("A_SKILL_PROMPT", "false").lower() in ("true", "1", "yes")
# E7/E8: compact label rules appended to the task A prompt only (ApertusClient.A_COMPACT_PROMPT_TEXT). On by default:
# the submission image sets no pipeline variables and runs these defaults. A_COMPACT_PROMPT=false restores the
# previous baseline, whose requests are byte-identical to 7c17c9c (tests/test_apertus_client.py)
A_COMPACT_PROMPT = os.getenv("A_COMPACT_PROMPT", "true").lower() in ("true", "1", "yes")
# Optional, hash-only audit of exact NLI inputs for paired prompt experiments.
PROMPT_INPUT_JOURNAL_PATH = os.getenv("PROMPT_INPUT_JOURNAL_PATH", "")

# 'ids' mode: a condensed system/user prompt with the same rules (fewer input tokens per case)
PROMPT_SHORT = os.getenv("PROMPT_SHORT", "false").lower() in ("true", "1", "yes")

# 'ids' mode: add worked examples for claims attributed to one side of the booklet
FEW_SHOT = os.getenv("FEW_SHOT", "false").lower() in ("true", "1", "yes")

# 'ids' mode: let the thinking model reason step by step before its JSON answer (much slower, more output tokens)
THINKING = os.getenv("THINKING", "false").lower() in ("true", "1", "yes")
THINKING_MAX_TOKENS = int(os.getenv("THINKING_MAX_TOKENS", "1500"))
# Hard reasoning budget in tokens (0 = none): when it runs out, the reasoning is closed and the answer forced
THINKING_BUDGET = int(os.getenv("THINKING_BUDGET", "0"))

# Cross-lingual pairs: translate the claim into the booklet language first (one extra short call) and give
# the model both the original and the translation
TRANSLATE_CLAIM = os.getenv("TRANSLATE_CLAIM", "false").lower() in ("true", "1", "yes")

# Speaker-aware retrieval: hide the opposing side's argument pages when a claim names who says something
SPEAKER_AWARE = os.getenv("SPEAKER_AWARE", "false").lower() in ("true", "1", "yes")

# Speaker boost: if a claim names one side, its N best argument pages are always among the retrieved pages
# (replacing the lowest-ranked other pages, so the page count stays NLI_TOP_K). Gold recall of committee claims
# 0.888 -> 0.985 with N=2 on all 1,495 pairs; macro-F1 0.931 -> 0.940 (22 fixed / 8 broken), no extra tokens
SPEAKER_BOOST = int(os.getenv("SPEAKER_BOOST", "2"))
# At most this many pages of the voting (legal) text among the retrieved pages (0 = no limit). The legal text repeats
# the vote title, so its pages often push the explanation pages out of the top k (experiment E1, 2026-10-11: rejected,
# claims about the legal text lose context)
LEGAL_TEXT_MAX_PAGES = int(os.getenv("LEGAL_TEXT_MAX_PAGES", "0"))
# Task B: a reference longer than this many characters is sent as its first chunk plus the chunks that best match the
# claim (BM25 with the claim and, if the languages differ, its translation), in document order, up to this budget
# (0 = always the whole reference). Experiment E2: all 1,488 task B cases macro-F1 0.981 -> 0.984 at -30 % input
# tokens; untouched holdout (27 Sep 2026 booklets, 90 claims) 0.955 -> 0.966 at -13 %
REFERENCE_MAX_CHARS = int(os.getenv("REFERENCE_MAX_CHARS", "6000"))
# Task B, tiered budget (experiment E17a, adopted: 1,488 cases macro-F1 0.9845 -> 0.9872, input tokens -5 %): a reference of at most REFERENCE_LONG_CHARS characters is cut
# to REFERENCE_MID_CHARS instead of REFERENCE_MAX_CHARS (0 = one budget for every length). References above
# REFERENCE_LONG_CHARS are almost all neutral claims whose cut lost F1 in E15, so they keep the larger budget.
REFERENCE_MID_CHARS = int(os.getenv("REFERENCE_MID_CHARS", "3000"))
REFERENCE_LONG_CHARS = int(os.getenv("REFERENCE_LONG_CHARS", "9000"))
# Speaker hint: tell the model which passages are the named side's own text
SPEAKER_HINT = os.getenv("SPEAKER_HINT", "false").lower() in ("true", "1", "yes")

# Hard override of the model label on a detected numerical clash.
# Off by default: on the OST benchmark it flipped correct Neutral predictions to Contradiction
# (claims citing a year the booklet never mentions are Neutral, not contradicted).
NUMERIC_OVERRIDE = os.getenv("NUMERIC_OVERRIDE", "false").lower() in ("true", "1", "yes")

# Evidence (task A, Hit@5) rebuilt from the cited pages as read by PyMuPDF: up to three whole pages plus the two
# text blocks that best match claim and vote ('raw_pages_and_blocks', Josip). Replayed with the official evaluate.py
# on the same predictions: dev 300 Hit@5 0.792 -> 0.872, test 401 0.727 -> 0.813 ('legacy' = the split pages below;
# the same blocks from pypdf or pypdfium2 text reach only 0.80 / 0.73: the gold passages follow PyMuPDF's text)
EVIDENCE_POLICY = os.getenv("EVIDENCE_POLICY", "raw_pages_and_blocks")
if EVIDENCE_POLICY not in ("legacy", "raw_pages", "raw_pages_and_blocks"):
    raise ValueError("Unsupported EVIDENCE_POLICY")
CACHE_SINGLE_FLIGHT = os.getenv("CACHE_SINGLE_FLIGHT", "false").lower() in ("true", "1", "yes")
# Read only the cited pages with PyMuPDF (not the whole booklet): processing time is scored
SOURCE_PAGES_LAZY = os.getenv("SOURCE_PAGES_LAZY", "true").lower() in ("true", "1", "yes")
# Cross-lingual claims: BM25 retrieves with the claim and its translation into the booklet language ('union', one
# short extra request; the NLI prompt keeps the original claim). Paired against 'original': dev 300 (Felipe) 7 fixed /
# 4 broken, macro-F1 0.934 -> 0.944; all 1,488 task-A cases (Josip, R2) 30 / 16, 0.948 -> 0.956; together 37 / 20
# (sign test p ~ 0.03) for ~3 % more tokens
RETRIEVAL_QUERY_MODE = os.getenv("RETRIEVAL_QUERY_MODE", "union")
if RETRIEVAL_QUERY_MODE not in ("original", "translated", "union"):
    raise ValueError("Unsupported RETRIEVAL_QUERY_MODE")
QUERY_TRANSLATION_CACHE_DIR = Path(os.getenv("QUERY_TRANSLATION_CACHE_DIR", str(Path(tempfile.gettempdir()) / "fact-attack" / "queries")))

# Mock Mode (useful for offline testing or prior to receiving CSCS key)
MOCK_APERTUS = os.getenv("MOCK_APERTUS", "false").lower() in ("true", "1", "yes")

# Challenge Label Mappings
LABEL_MAPPING = {
    0: "Entailment",
    1: "Neutral",
    2: "Contradiction",
}

LABEL_EXPLANATIONS = {
    0: "The booklet supports the statement.",
    1: "The booklet does not provide enough information either way.",
    2: "The booklet contradicts the statement.",
}

# Parsed booklets are cached on disk, keyed by file content (so a re-mounted PDF path still hits the cache).
# New entries go to BOOKLET_CACHE_DIR (the Docker image sets it to /tmp, the only writable cache location at
# evaluation); BOOKLET_CACHE_PREBUILT is a read-only cache baked into the image at build time
BOOKLET_CACHE_DIR = Path(os.getenv("BOOKLET_CACHE_DIR", str(Path(tempfile.gettempdir()) / "fact-attack" / "booklets")))
BOOKLET_CACHE_PREBUILT = Path(os.getenv("BOOKLET_CACHE_PREBUILT", str(BASE_DIR / ".cache" / "booklets")))

# Evidence (task A, Hit@5): the first cited pages cut into pieces ('2,2' = first two cited pages in halves), the
# remaining slots filled with the best-matching third of further pages (other cited pages, then retrieved ones).
# Official evaluate.py, replayed on saved runs: dev 300 Hit@5 0.763 ('3,2', no fill) -> 0.810, test 0.603 -> 0.749.
# At most EVIDENCE_MAX_ITEMS items (only five are scored) of at most EVIDENCE_MAX_CHARS each
EVIDENCE_SPLIT = os.getenv("EVIDENCE_SPLIT", "2,2")
EVIDENCE_FILL = os.getenv("EVIDENCE_FILL", "true").lower() in ("true", "1", "yes")
EVIDENCE_MAX_ITEMS = int(os.getenv("EVIDENCE_MAX_ITEMS", "5"))
EVIDENCE_MAX_CHARS = int(os.getenv("EVIDENCE_MAX_CHARS", "4800"))
# Also give evidence (the top-ranked pages) for Neutral answers; it is scored for gold entailment/contradiction
# cases whatever the predicted label, but the contract only asks for it with labels 0/2
EVIDENCE_ON_NEUTRAL = os.getenv("EVIDENCE_ON_NEUTRAL", "false").lower() in ("true", "1", "yes")

# Parallel cases in the batch CLI: parsing and retrieval of one case overlap with LLM requests of others, so
# they do not count as processing time (wall clock minus time with an LLM request in flight)
BATCH_WORKERS = int(os.getenv("NLI_BATCH_WORKERS") or os.getenv("NLI_WORKERS") or "4")  # both names accepted

# Directories
DATA_DIR = BASE_DIR / "data"
BOOKLETS_DIR = DATA_DIR / "booklets"
BENCHMARK_PATH = DATA_DIR / "demo_dataset.jsonl"
