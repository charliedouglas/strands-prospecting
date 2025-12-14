"""
Data models for the prospecting agent.

This module exports all Pydantic models used throughout the application,
including planning models, result models, and prospect entity models.
"""

# Shared models (used across multiple agents)
from .shared import (
    ClarificationRequest,
)

# Planning models
from .plan import (
    DataSource,
    PlanStep,
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

# Sufficiency checking models
from .sufficiency import (
    SufficiencyStatus,
    SufficiencyResult,
)

# Rebuild models to resolve forward references
# Pass the current namespace so Pydantic can resolve forward reference strings
_namespace = {
    'AggregatedResults': AggregatedResults,
    'ClarificationRequest': ClarificationRequest,
}
AggregatedResults.model_rebuild()
SufficiencyResult.model_rebuild(_types_namespace=_namespace)

__all__ = [
    # Shared
    "ClarificationRequest",
    # Planning
    "DataSource",
    "PlanStep",
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
    # Sufficiency
    "SufficiencyStatus",
    "SufficiencyResult",
]
