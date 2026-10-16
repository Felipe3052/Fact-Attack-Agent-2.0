"""
Agent State Definition for LangGraph (SW5 Folie 10).
Contains standardized raw facts/data passed between nodes.
"""
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langgraph.graph import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    claim: str
    booklet_path: str
    vote_title: Optional[str]
    detected_language: str
    source_part: Optional[str]
    candidate_pages: List[int]
    context_text: str
    evidence_blocks: List[Dict[str, Any]]
    verdict: Optional[Dict[str, Any]]
    audit: Optional[Dict[str, Any]]
    audit_passed: bool
    audit_retries: int
    needs_human_clarification: bool
    final_response: str
