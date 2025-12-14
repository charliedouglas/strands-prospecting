"""
Planning models for the prospecting agent.

This module defines the data structures used in the planning phase,
including data sources, plan steps, and execution plans.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

from .shared import ClarificationRequest


class DataSource(str, Enum):
    """
    Enumeration of available data sources for prospecting.

    Each source provides specific types of information:
    - ORBIS: Corporate structures, financials, ownership, directors
    - WEALTHX: UHNW profiles, wealth composition, interests, connections
    - WEALTH_MONITOR: UK-specific wealth data, property, shareholdings
    - COMPANIES_HOUSE: UK company filings, PSCs, directorships
    - DUN_BRADSTREET: Credit risk, business signals, firmographics
    - CRUNCHBASE: Funding rounds, startup ecosystem, investors
    - PITCHBOOK: PE/VC deals, private valuations, investor networks
    - SERPAPI: News search, recent events
    - INTERNAL_CRM: Existing client check, exclusions
    """
    ORBIS = "orbis"
    WEALTHX = "wealthx"
    WEALTH_MONITOR = "wealth_monitor"
    COMPANIES_HOUSE = "companies_house"
    DUN_BRADSTREET = "dun_bradstreet"
    CRUNCHBASE = "crunchbase"
    PITCHBOOK = "pitchbook"
    SERPAPI = "serpapi"
    INTERNAL_CRM = "internal_crm"


class PlanStep(BaseModel):
    """
    A single step in an execution plan.

    Represents one data source query with its parameters, dependencies,
    and reasoning.
    """
    step_id: int = Field(..., description="Unique identifier for this step")
    source: DataSource = Field(..., description="Data source to query")
    action: str = Field(..., description="Specific action to perform, e.g., 'search_funding', 'get_directors'")
    params: dict = Field(default_factory=dict, description="Source-specific parameters for the query")
    reason: str = Field(..., description="Explanation of why this step is needed")
    depends_on: list[int] = Field(default_factory=list, description="Step IDs that must complete before this step")

    class Config:
        json_schema_extra = {
            "example": {
                "step_id": 1,
                "source": "crunchbase",
                "action": "search_funding",
                "params": {
                    "investment_type": "series_b",
                    "location": "united-kingdom",
                    "announced_on_gte": "2023-01-01"
                },
                "reason": "Find UK companies with Series B funding",
                "depends_on": []
            }
        }


class ExecutionPlan(BaseModel):
    """
    Complete execution plan for a prospecting query.

    Contains the reasoning, ordered steps, any clarification needed,
    and metadata about the plan.
    """
    reasoning: str = Field(..., description="Chain of thought from the planner explaining the strategy")
    steps: list[PlanStep] = Field(default_factory=list, description="Ordered list of execution steps")
    clarification_needed: Optional[ClarificationRequest] = Field(
        None,
        description="Clarification request if the query is ambiguous"
    )
    estimated_sources: int = Field(..., description="Number of unique data sources to be queried")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Planner's confidence in the plan (0-1)")

    class Config:
        json_schema_extra = {
            "example": {
                "reasoning": "To find UK tech companies with Series B funding and female founders, I'll: 1) Query Crunchbase for funding rounds, 2) Cross-reference with PitchBook, 3) Get director info from Companies House, 4) Enrich profiles via Wealth-X, 5) Check CRM for existing relationships",
                "steps": [
                    {
                        "step_id": 1,
                        "source": "crunchbase",
                        "action": "search_funding",
                        "params": {"investment_type": "series_b", "location": "united-kingdom"},
                        "reason": "Find UK Series B rounds",
                        "depends_on": []
                    }
                ],
                "clarification_needed": None,
                "estimated_sources": 5,
                "confidence": 0.85
            }
        }
