"""CLI-based approval handler for the prospecting system."""

import logging
from typing import Optional

from src.approval_handler import ApprovalHandler
from src.models import PlanSummary, UserFeedback, ApprovalStatus
from src.session import CLIFormatter

logger = logging.getLogger(__name__)


class CLIApprovalHandler(ApprovalHandler):
    """
    CLI-based implementation of the ApprovalHandler.

    Presents plan summaries to users and collects their approval decisions
    via standard input/output.
    """

    async def request_approval(
        self,
        summary: PlanSummary,
        revision_number: int
    ) -> UserFeedback:
        """
        Request approval from the user for an execution plan.

        Args:
            summary: Human-friendly summary of the execution plan
            revision_number: Which revision this is (1 for first, 2+ for revisions)

        Returns:
            UserFeedback with the user's decision
        """
        # Show plan summary
        print(CLIFormatter.section("Execution Plan Review"))

        if revision_number > 1:
            print(f"\n{CLIFormatter.info('This is revision ' + str(revision_number))}\n")

        print(f"Reasoning: {summary.reasoning}\n")

        if summary.steps:
            print("Steps to execute:")
            for i, step in enumerate(summary.steps, 1):
                print(f"  {i}. {step}")
            print()

        print(f"Estimated data sources: {summary.estimated_sources}")
        print(f"Planner confidence: {summary.confidence:.0%}\n")

        # Get user decision
        while True:
            print("Do you want to proceed? (approve/modify/reject)")
            decision = input("> ").strip().lower()

            if decision in ["approve", "a", "yes", "y"]:
                return UserFeedback(
                    status=ApprovalStatus.APPROVED,
                    feedback_text=None
                )

            elif decision in ["modify", "m", "revise", "r"]:
                feedback = input(
                    "What would you like to change or clarify?\n> "
                ).strip()
                if feedback:
                    return UserFeedback(
                        status=ApprovalStatus.NEEDS_REVISION,
                        feedback_text=feedback
                    )
                else:
                    print(CLIFormatter.warning("Please provide your feedback"))
                    continue

            elif decision in ["reject", "no", "n"]:
                return UserFeedback(
                    status=ApprovalStatus.REJECTED,
                    feedback_text=None
                )

            else:
                print(CLIFormatter.warning(
                    "Please enter 'approve', 'modify', or 'reject'"
                ))
