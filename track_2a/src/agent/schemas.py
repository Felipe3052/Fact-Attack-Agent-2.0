"""
Pydantic Schemas for Fact Attack Agent 2.0.
Structured Outputs and Data Validation conforming to Course SW5.
"""
from typing import List, Optional
from pydantic import BaseModel, Field

class ClaimAnalysis(BaseModel):
    """Initial linguistic and domain analysis of the user's claim."""
    claim: str = Field(description="The original claim text.")
    detected_language: str = Field(description="Detected language code: 'de', 'fr', or 'it'.")
    source_actor: Optional[str] = Field(
        default=None,
        description="Actor or section indicated in the opening (e.g. 'committee', 'federal_council', 'summary', 'legal_text')."
    )
    detected_vote: Optional[str] = Field(
        default=None,
        description="Identified voting proposal/initiative title, if present or inferred."
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in proposal and source identification."
    )

class ClaimVerdict(BaseModel):
    """Structured NLI verification result."""
    label: int = Field(
        description="0 for Entailment (supported), 1 for Neutral (unsettled / not mentioned), 2 for Contradiction (refuted)."
    )
    label_name: str = Field(
        description="'entailment', 'neutral', or 'contradiction'."
    )
    justification: str = Field(
        description="Concise rationale (max 3-4 sentences) justifying the decision strictly against official booklet text."
    )
    cited_pages: List[int] = Field(
        default_factory=list,
        description="List of 1-based physical booklet page numbers that provide direct evidence."
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Estimated probability or confidence score."
    )

class EvidenceAudit(BaseModel):
    """Audit result from the LLM-as-a-Judge node."""
    is_faithful: bool = Field(
        description="True if the justification and label are strictly grounded in the cited booklet text without hallucination."
    )
    citations_valid: bool = Field(
        description="True if the cited pages actually contain the relevant discussion."
    )
    score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Faithfulness score from 0.0 to 1.0."
    )
    feedback: Optional[str] = Field(
        default=None,
        description="Explanation or critique if audit failed."
    )
