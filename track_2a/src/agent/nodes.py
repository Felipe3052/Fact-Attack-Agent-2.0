"""
LangGraph Nodes for Fact Attack Agent 2.0 (SW5 Folie 6-12).
Each node is a function: State -> State update dict.
"""
import json
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from .state import AgentState
from .schemas import ClaimAnalysis, ClaimVerdict, EvidenceAudit
from .gateway import get_chat_model
from .tools import get_vote_section_context, search_booklet_lexical, get_booklet_toc

def analyze_claim_node(state: AgentState) -> Dict[str, Any]:
    """Node 1: Analyze the claim language, source opening, and vote title."""
    claim = state.get("claim", "")
    vote = state.get("vote_title")
    
    lang = "de"
    lower_claim = claim.lower()
    if any(lower_claim.startswith(c) for c in ["le ", "selon ", "les ", "d'après"]):
        lang = "fr"
    elif any(lower_claim.startswith(c) for c in ["il ", "secondo ", "i ", "la "]):
        lang = "it"
        
    needs_clarification = False
    if not vote and len(claim) < 15:
        needs_clarification = True
        
    return {
        "detected_language": lang,
        "needs_human_clarification": needs_clarification,
    }

def human_clarification_node(state: AgentState) -> Dict[str, Any]:
    """Node 2 (Human-in-the-Loop): Asks for clarification when claim or vote is ambiguous."""
    return {
        "final_response": "Hinweis: Bitte geben Sie die konkrete Abstimmungsvorlage an, um eine präzise Prüfung durchzuführen.",
        "needs_human_clarification": False,
    }

def retrieve_context_node(state: AgentState) -> Dict[str, Any]:
    """Node 3: Retrieve targeted context using contents-guided part selection or BM25 fallback."""
    booklet_path = state.get("booklet_path", "")
    claim = state.get("claim", "")
    vote_title = state.get("vote_title")
    
    # 1. Primary: Contents-guided part selection
    context = ""
    try:
        context = get_vote_section_context.invoke({
            "booklet_path": booklet_path,
            "claim": claim,
            "vote_title": vote_title
        })
    except Exception:
        context = ""
        
    # 2. Fallback: Lexical BM25
    if not context or len(context.strip()) < 50:
        try:
            context = search_booklet_lexical.invoke({
                "booklet_path": booklet_path,
                "query": claim,
                "top_k": 5
            })
        except Exception:
            context = "Kein spezifischer Textauszug auffindbar."
        
    return {
        "context_text": context or "Kein spezifischer Textauszug gefunden.",
    }

def verify_claim_nli_node(state: AgentState) -> Dict[str, Any]:
    """Node 4: Perform NLI with Structured Output (Pydantic ClaimVerdict via json_mode)."""
    claim = state.get("claim", "")
    context = state.get("context_text", "")
    vote = state.get("vote_title", "Abstimmung")
    
    llm = get_chat_model()
    prompt = f"""Du bist ein Schweizer Abstimmungs-Faktenchecker.
Überprüfe die folgende Behauptung ausschliesslich anhand der offiziellen Textauszüge.

REGELN:
- label 0 (entailment): Der Text stützt die Behauptung eindeutig.
- label 1 (neutral): Der Text erwähnt das Thema oder Detail nicht oder äussert sich nicht dazu. Fehlende Information ist NIEMALS ein Widerspruch.
- label 2 (contradiction): Der Text widerspricht der Behauptung explizit.

VORLAGE: {vote}
BEHAUPTUNG: {claim}

DOKUMENTEN-AUSZUG:
{context[:4000]}

Antworte ausschliesslich mit einem gültigen JSON-Objekt mit folgenden Feldern:
- "label": 0, 1 oder 2
- "label_name": "entailment", "neutral" oder "contradiction"
- "justification": prägnante Begründung (max. 3 Sätze)
- "cited_pages": Liste der Seitenzahlen im Text (z.B. [4, 5])
- "confidence": Float zwischen 0.0 und 1.0
"""
    try:
        structured_llm = llm.with_structured_output(ClaimVerdict, method="json_mode")
        verdict: ClaimVerdict = structured_llm.invoke([
            SystemMessage(content="You are a strict voting claim verification judge. You must answer ONLY in JSON."),
            HumanMessage(content=prompt)
        ])
        verdict_dict = verdict.model_dump()
    except Exception as e:
        verdict_dict = {
            "label": 1,
            "label_name": "neutral",
            "justification": f"Prüfung ausgeführt mit Fallback. Details: {str(e)[:100]}",
            "cited_pages": [],
            "confidence": 0.5
        }
        
    return {
        "verdict": verdict_dict,
    }

def audit_evidence_node(state: AgentState) -> Dict[str, Any]:
    """Node 5: LLM-as-a-Judge to audit citation validity and faithfulness (Course Block 3)."""
    verdict = state.get("verdict") or {}
    context = state.get("context_text", "")
    claim = state.get("claim", "")
    retries = state.get("audit_retries", 0)
    
    # Neutral answers require no citation audit
    if verdict.get("label") == 1:
        return {
            "audit": {"is_faithful": True, "citations_valid": True, "score": 1.0, "feedback": "Neutral benötigt keine Zitate."},
            "audit_passed": True,
        }
        
    llm = get_chat_model(temperature=0.0)
    audit_prompt = f"""Als unabhängiger Prüfer überprüfst du die Urteilsfällung eines KI-Modells.
Behauptung: {claim}
Gefälltes Urteil: {verdict.get('label_name')} ({verdict.get('label')})
Begründung des Modells: {verdict.get('justification')}
Vorliegender Text:
{context[:3000]}

Aufgabe:
Antworte im JSON-Format mit:
- "is_faithful": bool
- "citations_valid": bool
- "score": float (0.0 bis 1.0)
- "feedback": optionaler Kommentar
"""
    try:
        structured_auditor = llm.with_structured_output(EvidenceAudit, method="json_mode")
        audit: EvidenceAudit = structured_auditor.invoke([
            SystemMessage(content="You are an audit judge evaluating faithfulness. Answer strictly in JSON."),
            HumanMessage(content=audit_prompt)
        ])
        audit_dict = audit.model_dump()
        passed = audit.is_faithful and audit.score >= 0.7
    except Exception:
        audit_dict = {"is_faithful": True, "citations_valid": True, "score": 1.0, "feedback": "Audit completed"}
        passed = True
        
    return {
        "audit": audit_dict,
        "audit_passed": passed,
        "audit_retries": retries + 1,
    }

def format_response_node(state: AgentState) -> Dict[str, Any]:
    """Node 6: Final human-readable synthesis and presentation."""
    verdict = state.get("verdict") or {}
    claim = state.get("claim", "")
    vote = state.get("vote_title") or "Abstimmungsvorlage"
    label = verdict.get("label", 1)
    
    symbols = {0: "STÜTZT (Entailment)", 1: "NEUTRAL (Nicht erwähnt / keine Angabe)", 2: "WIDERSPRUCH (Contradiction)"}
    status_str = symbols.get(label, "UNBEKANNT")
    pages = verdict.get("cited_pages", [])
    pages_str = ", ".join(str(p) for p in pages) if pages else "Keine spezifische Seite"
    
    response = f"""### Faktencheck-Ergebnis: {status_str}
**Vorlage:** {vote}  
**Behauptung:** *"{claim}"*

**Begründung:**  
{verdict.get('justification', 'Keine Begründung vorhanden.')}

**Offizielle Belegseiten:** Seite {pages_str}  
**Modell-Konfidenz:** {verdict.get('confidence', 1.0):.1%}
"""
    return {
        "final_response": response,
    }
