"""
Result models for the prospecting agent.

This module defines data structures for search results and aggregated results
from multiple data sources.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Union, TYPE_CHECKING

from .plan import DataSource

if TYPE_CHECKING:
    from .plan import ExecutionPlan
    from .prospect import Company, Individual


class SearchResult(BaseModel):
    """
    Result from a single data source query.

    Captures the outcome of executing one step in the execution plan,
    including success/failure, data, errors, and timing.
    """
    step_id: int = Field(..., description="ID of the plan step that produced this result")
    source: DataSource = Field(..., description="Data source that was queried")
    success: bool = Field(..., description="Whether the query succeeded")
    data: Optional[Union[dict, list]] = Field(None, description="Raw response data from the source")
    error: Optional[str] = Field(None, description="Error message if the query failed")
    record_count: int = Field(0, description="Number of records returned")
    execution_time_ms: int = Field(..., description="Time taken to execute the query in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the query was executed")

    class Config:
        json_schema_extra = {
            "example": {
                "step_id": 1,
                "source": "crunchbase",
                "success": True,
                "data": {
                    "count": 15,
                    "entities": [
                        {
                            "uuid": "abc123",
                            "properties": {
                                "identifier": {"value": "ACME Technologies"},
                                "money_raised": {"value": 25000000, "currency": "GBP"}
                            }
                        }
                    ]
                },
                "error": None,
                "record_count": 15,
                "execution_time_ms": 342,
                "timestamp": "2024-12-12T10:30:00Z"
            }
        }


class AggregatedResults(BaseModel):
    """
    Aggregated results from all data source queries.

    Contains the original query, execution plan, raw results, and
    deduplicated/normalized entities (companies and individuals).
    """
    original_query: str = Field(..., description="The original user query")
    plan: "ExecutionPlan" = Field(..., description="The execution plan that was followed")
    results: list[SearchResult] = Field(default_factory=list, description="Raw results from each data source query")
    companies: list["Company"] = Field(default_factory=list, description="Deduplicated companies found across all sources")
    individuals: list["Individual"] = Field(default_factory=list, description="Deduplicated individuals found across all sources")
    total_records: int = Field(0, description="Total number of records returned across all sources")
    sources_queried: list[DataSource] = Field(default_factory=list, description="List of data sources that were queried")
    execution_time_ms: int = Field(..., description="Total execution time for all queries in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "original_query": "Find UK tech companies that raised Series B in 2024",
                "plan": {
                    "reasoning": "Query Crunchbase and PitchBook for Series B rounds...",
                    "steps": [],
                    "clarification_needed": None,
                    "estimated_sources": 3,
                    "confidence": 0.85
                },
                "results": [],
                "companies": [],
                "individuals": [],
                "total_records": 45,
                "sources_queried": ["crunchbase", "pitchbook", "companies_house"],
                "execution_time_ms": 1523
            }
        }
