"""
Approval handler interface for the prospecting system.

This module defines the abstract interface for approval handlers,
enabling different implementations (CLI, API, etc.) to be used
interchangeably with the orchestrator.
"""

from abc import ABC, abstractmethod

from src.models import PlanSummary, UserFeedback


class ApprovalHandler(ABC):
    """
    Abstract base class for approval handlers.

    Approval handlers are responsible for presenting plan summaries to users
    and collecting their approval decisions and feedback. Different implementations
    can support different interfaces (CLI, REST API, webhook, etc.).
    """

    @abstractmethod
    async def request_approval(
        self,
        summary: PlanSummary,
        revision_number: int
    ) -> UserFeedback:
        """
        Request approval from the user for an execution plan.

        This method should:
        1. Present the plan summary to the user in an appropriate format
        2. Wait for the user's decision (approve, modify, or reject)
        3. Collect any feedback if the user requests modifications
        4. Return the user's decision and feedback

        Args:
            summary: Human-friendly summary of the execution plan
            revision_number: Which revision this is (1 for first presentation, 2+ for revisions)

        Returns:
            UserFeedback object containing the user's decision and any feedback text

        Raises:
            Exception: Implementation-specific exceptions for handling errors
                      (e.g., timeout, communication failure, etc.)
        """
        pass
