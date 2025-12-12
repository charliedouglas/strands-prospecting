"""
Data models for the prospecting agent.

This module exports all Pydantic models used throughout the application,
including planning models, result models, and prospect entity models.
"""

# Planning models
from .plan import (
    DataSource,
    PlanStep,
    ClarificationRequest,
    ExecutionPlan,
)

# Result models
from .results import (
    SearchResult,
    AggregatedResults,
)

# Prospect entity models
from .prospect import (
    Role,
    Company,
    Individual,
)

# Approval workflow models
from .approval import (
    ApprovalStatus,
    UserFeedback,
    PlanSummary,
    PlanRevision,
    ApprovalWorkflowState,
    WorkflowRejectedError,
)

# Rebuild models to resolve forward references
AggregatedResults.model_rebuild()

__all__ = [
    # Planning
    "DataSource",
    "PlanStep",
    "ClarificationRequest",
    "ExecutionPlan",
    # Results
    "SearchResult",
    "AggregatedResults",
    # Prospects
    "Role",
    "Company",
    "Individual",
    # Approval workflow
    "ApprovalStatus",
    "UserFeedback",
    "PlanSummary",
    "PlanRevision",
    "ApprovalWorkflowState",
    "WorkflowRejectedError",
]
