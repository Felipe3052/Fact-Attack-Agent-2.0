"""
Unit tests for Fact Attack Agent 2.0 LangGraph Workflow.
"""
import pytest
from src.agent.state import AgentState
from src.agent.schemas import ClaimVerdict, EvidenceAudit
from src.agent.workflow import build_fact_check_graph

def test_graph_compilation():
    graph = build_fact_check_graph()
    assert graph is not None

def test_claim_verdict_schema():
    v = ClaimVerdict(
        label=0,
        label_name="entailment",
        justification="Text supports claim.",
        cited_pages=[4, 5],
        confidence=0.98
    )
    assert v.label == 0
    assert len(v.cited_pages) == 2

def test_evidence_audit_schema():
    a = EvidenceAudit(
        is_faithful=True,
        citations_valid=True,
        score=0.95
    )
    assert a.is_faithful is True
    assert a.score == 0.95
