"""
Sufficiency checking models for the prospecting agent.

This module defines data structures used in the sufficiency checking phase,
including status types and results.
"""

from pydantic import BaseModel, Field
from typing import Optional, TYPE_CHECKING
from enum import Enum

from .shared import ClarificationRequest

if TYPE_CHECKING:
    from .results import AggregatedResults


class SufficiencyStatus(str, Enum):
    """
    Status of sufficiency check.

    - SUFFICIENT: Data answers the query, proceed to report generation
    - CLARIFICATION_NEEDED: Need user input to refine the search
    - RETRY_NEEDED: Should re-run certain steps with modified parameters
    """
    SUFFICIENT = "sufficient"
    CLARIFICATION_NEEDED = "clarification_needed"
    RETRY_NEEDED = "retry_needed"


class SufficiencyResult(BaseModel):
    """
    Result from the sufficiency checker.

    Evaluates whether the gathered data adequately answers the original query,
    and provides guidance on next steps.
    """
    status: SufficiencyStatus = Field(..., description="Overall sufficiency status")
    reasoning: str = Field(..., description="Detailed reasoning for the sufficiency decision")
    gaps: list[str] = Field(default_factory=list, description="Specific data gaps identified")
    clarification: Optional[ClarificationRequest] = Field(
        None,
        description="Clarification request if more information is needed from the user"
    )
    retry_steps: list[int] = Field(
        default_factory=list,
        description="Step IDs that should be retried (for RETRY_NEEDED status)"
    )
    filtered_results: Optional["AggregatedResults"] = Field(
        None,
        description="Results with exclusions applied (e.g., existing clients filtered)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "sufficient",
                "reasoning": "The data gathered provides complete information about UK tech companies with Series B funding. We found 15 companies through Crunchbase and PitchBook, obtained director information from Companies House for all of them, and verified none are existing clients.",
                "gaps": [],
                "clarification": None,
                "retry_steps": [],
                "filtered_results": None
            }
        }
