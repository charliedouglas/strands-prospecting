"""
Shared models used across multiple agents in the prospecting system.

This module contains data structures that are used by multiple agents
and don't belong to a specific domain (planning, results, etc.).
"""

from pydantic import BaseModel, Field
from typing import Optional


class ClarificationRequest(BaseModel):
    """
    Request for user clarification when additional information is needed.

    Used by multiple agents (Planner, Sufficiency Checker) when they need
    user input to proceed effectively.

    Supports both multiple choice (via options) and custom user input.
    When allow_custom_input is True, a final option for free-form text
    entry will be presented to the user.
    """
    question: str = Field(..., description="The clarification question to ask the user")
    options: Optional[list[str]] = Field(None, description="Optional multiple choice options for the user")
    context: str = Field(..., description="Explanation of why this clarification is needed")
    allow_custom_input: bool = Field(
        default=True,
        description="Whether to allow custom user input in addition to predefined options"
    )
    custom_input_label: str = Field(
        default="Other (please specify)",
        description="Label for the custom input option when allow_custom_input is True"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Which region would you like to focus on?",
                "options": ["London", "Manchester", "Edinburgh", "All UK"],
                "context": "The query mentions 'UK tech companies' but filtering by region will provide more targeted results",
                "allow_custom_input": True,
                "custom_input_label": "Other region (please specify)"
            }
        }
