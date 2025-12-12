"""
Approval workflow models for the prospecting agent.

This module defines the data structures used in the approval workflow,
including approval statuses, user feedback, plan summaries, and workflow state.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from src.models.plan import ExecutionPlan


class ApprovalStatus(str, Enum):
    """
    Status of a plan approval request.

    - PENDING: Waiting for user input
    - APPROVED: User approved the plan
    - REJECTED: User rejected the plan
    - NEEDS_REVISION: User requested modifications
    """
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class UserFeedback(BaseModel):
    """
    Captures user's response to a plan presentation.

    This model records what the user decided and any feedback
    they provided for plan revisions.
    """
    status: ApprovalStatus = Field(..., description="User's approval decision")
    feedback_text: Optional[str] = Field(
        None,
        description="User's modification requests or comments"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the feedback was provided"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "needs_revision",
                "feedback_text": "Can you also check PitchBook for more recent funding data?",
                "timestamp": "2024-12-12T10:30:00"
            }
        }


class PlanSummary(BaseModel):
    """
    Human-friendly summary of an ExecutionPlan.

    This model presents the plan in a way that's easy for users to understand,
    hiding technical details while highlighting key information.
    """
    query: str = Field(..., description="Original user query")
    data_sources: list[str] = Field(
        default_factory=list,
        description="Names of data sources that will be queried (e.g., 'Crunchbase', 'Companies House')"
    )
    key_actions: list[str] = Field(
        default_factory=list,
        description="High-level description of what will happen in each step"
    )
    estimated_sources: int = Field(..., description="Number of unique data sources")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Planner's confidence in the plan (0-1)")
    reasoning_summary: str = Field(..., description="Condensed version of planner's reasoning")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Find UK tech companies that raised Series B in the last 12 months",
                "data_sources": ["Crunchbase", "PitchBook", "Companies House", "Internal CRM"],
                "key_actions": [
                    "Search for Series B funding rounds in UK tech sector",
                    "Cross-reference funding data with PitchBook",
                    "Get company officer information from Companies House",
                    "Check if any companies are existing clients"
                ],
                "estimated_sources": 4,
                "confidence": 0.85,
                "reasoning_summary": "Will use Crunchbase and PitchBook for funding data, Companies House for corporate structure, and CRM to filter existing relationships."
            }
        }


class PlanRevision(BaseModel):
    """
    Tracks a single revision of an execution plan.

    Records the plan presented to the user, the summary they saw,
    and their feedback for this revision.
    """
    revision_number: int = Field(..., ge=1, description="Sequential revision number (starts at 1)")
    original_plan: ExecutionPlan = Field(..., description="The execution plan for this revision")
    summary: PlanSummary = Field(..., description="The human-friendly summary presented to the user")
    user_feedback: Optional[UserFeedback] = Field(
        None,
        description="User's feedback on this revision (None if still pending)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this revision was created"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "revision_number": 1,
                "original_plan": {"reasoning": "...", "steps": []},
                "summary": {"query": "...", "data_sources": []},
                "user_feedback": {"status": "needs_revision", "feedback_text": "..."},
                "timestamp": "2024-12-12T10:30:00"
            }
        }


class ApprovalWorkflowState(BaseModel):
    """
    Tracks the complete state of an approval workflow.

    This model maintains the full history of revisions and the current
    status of the approval process.
    """
    query: str = Field(..., description="Original user query")
    revisions: list[PlanRevision] = Field(
        default_factory=list,
        description="Complete history of plan revisions and user feedback"
    )
    current_status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING,
        description="Current status of the workflow"
    )
    final_approved_plan: Optional[ExecutionPlan] = Field(
        None,
        description="The plan that was ultimately approved (None if not yet approved)"
    )

    @property
    def current_revision_number(self) -> int:
        """Get the current revision number."""
        return len(self.revisions)

    @property
    def is_complete(self) -> bool:
        """Check if the workflow is complete (approved or rejected)."""
        return self.current_status in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED)

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Find UK tech companies that raised Series B in the last 12 months",
                "revisions": [
                    {
                        "revision_number": 1,
                        "original_plan": {"reasoning": "...", "steps": []},
                        "summary": {"query": "...", "data_sources": []},
                        "user_feedback": {"status": "needs_revision"}
                    }
                ],
                "current_status": "pending",
                "final_approved_plan": None
            }
        }


class WorkflowRejectedError(Exception):
    """Exception raised when a user rejects an approval workflow."""
    pass
