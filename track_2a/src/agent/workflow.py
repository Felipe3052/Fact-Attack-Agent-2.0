"""
LangGraph StateGraph Builder & Compilation (SW5 Folie 11-12).
Assembles nodes and conditional edges into an executable agent.
"""
from langgraph.graph import StateGraph, START, END
from .state import AgentState
from .nodes import (
    analyze_claim_node,
    human_clarification_node,
    retrieve_context_node,
    verify_claim_nli_node,
    audit_evidence_node,
    format_response_node,
)
from .edges import route_after_analysis, route_after_audit

def build_fact_check_graph():
    """Builds and compiles the Fact Attack Agent 2.0 LangGraph workflow."""
    builder = StateGraph(AgentState)
    
    # 1. Add Nodes
    builder.add_node("analyze_claim", analyze_claim_node)
    builder.add_node("human_clarification", human_clarification_node)
    builder.add_node("retrieve_context", retrieve_context_node)
    builder.add_node("verify_claim_nli", verify_claim_nli_node)
    builder.add_node("audit_evidence", audit_evidence_node)
    builder.add_node("format_response", format_response_node)
    
    # 2. Add Edges
    builder.add_edge(START, "analyze_claim")
    
    builder.add_conditional_edges(
        "analyze_claim",
        route_after_analysis,
        {
            "human_clarification": "human_clarification",
            "retrieve_context": "retrieve_context",
        }
    )
    
    builder.add_edge("human_clarification", END)
    builder.add_edge("retrieve_context", "verify_claim_nli")
    builder.add_edge("verify_claim_nli", "audit_evidence")
    
    builder.add_conditional_edges(
        "audit_evidence",
        route_after_audit,
        {
            "retrieve_context": "retrieve_context",
            "format_response": "format_response",
        }
    )
    
    builder.add_edge("format_response", END)
    
    return builder.compile()
