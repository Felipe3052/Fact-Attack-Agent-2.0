"""
Conditional Edges and Routing Functions for LangGraph (SW5 Folie 8 & 19).
"""
from typing import Literal
from .state import AgentState

def route_after_analysis(state: AgentState) -> Literal["human_clarification", "retrieve_context"]:
    """Decides whether user clarification is needed before retrieving context."""
    if state.get("needs_human_clarification", False):
        return "human_clarification"
    return "retrieve_context"

def route_after_audit(state: AgentState) -> Literal["retrieve_context", "format_response"]:
    """Routes back to retrieval if LLM-as-a-Judge audit failed (self-correction loop), else to format."""
    passed = state.get("audit_passed", True)
    retries = state.get("audit_retries", 0)
    
    if not passed and retries < 2:
        return "retrieve_context"
    return "format_response"
