"""
Orchestrator for the prospecting system.

This module coordinates the end-to-end prospecting workflow, including
planning, approval, execution, and reporting.
"""

import logging
from datetime import datetime
from typing import Optional

from src.models import (
    ExecutionPlan,
    ApprovalStatus,
    ApprovalWorkflowState,
    PlanRevision,
    WorkflowRejectedError,
)
from src.agents.planner import PlannerAgent
from src.agents.summarizer import SummarizerAgent
from src.approval_handler import ApprovalHandler
from src.config import Settings

logger = logging.getLogger(__name__)


class ProspectingOrchestrator:
    """
    Main orchestrator for the prospecting workflow with user approval.

    This orchestrator coordinates the entire prospecting process:
    1. Query planning (with optional clarification)
    2. Plan approval loop (with revision support)
    3. Plan execution (when executor is implemented)
    4. Result validation (when sufficiency checker is implemented)
    5. Report generation (when reporter is implemented)
    """

    def __init__(
        self,
        settings: Settings,
        approval_handler: ApprovalHandler
    ):
        """
        Initialize the orchestrator.

        Args:
            settings: Application settings
            approval_handler: Handler for collecting user approval (CLI, API, etc.)
        """
        self.settings = settings
        self.approval_handler = approval_handler

        # Initialize agents
        self.planner = PlannerAgent(settings)
        self.summarizer = SummarizerAgent(settings)
        # TODO: Add executor, sufficiency checker, reporter when implemented

        logger.info("Prospecting orchestrator initialized")

    async def run(self, query: str) -> dict:
        """
        Run the complete prospecting workflow with user approval.

        This is the main entry point that coordinates all stages of the workflow.

        Args:
            query: The user's prospecting query

        Returns:
            Dictionary with workflow results (structure TBD when executor is implemented)

        Raises:
            WorkflowRejectedError: If the user rejects the plan
            ValueError: If planning or execution fails
        """
        logger.info(f"Starting prospecting workflow for query: {query}")

        # Initialize workflow state
        workflow_state = ApprovalWorkflowState(
            query=query,
            revisions=[],
            current_status=ApprovalStatus.PENDING,
            final_approved_plan=None
        )

        try:
            # Step 1: Create initial plan
            plan = await self._create_initial_plan(query)

            # Step 2: Handle clarification if needed
            if plan.clarification_needed:
                logger.info("Plan requires clarification from user")
                return await self._handle_clarification(plan)

            # Step 3: Approval loop
            approved_plan = await self._approval_loop(
                plan=plan,
                query=query,
                workflow_state=workflow_state
            )

            # Step 4: Execute approved plan
            # TODO: Implement when executor is ready
            logger.info("Plan approved - execution would start here")
            logger.info(f"Approved plan has {len(approved_plan.steps)} steps")

            # For now, return a placeholder result
            return {
                "status": "approved",
                "query": query,
                "plan": approved_plan.model_dump(),
                "workflow_state": workflow_state.model_dump(),
                "message": "Plan approved successfully. Execution will be implemented in the next phase."
            }

        except WorkflowRejectedError as e:
            logger.info(f"Workflow rejected by user: {e}")
            workflow_state.current_status = ApprovalStatus.REJECTED
            raise

        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            raise

    async def _create_initial_plan(self, query: str) -> ExecutionPlan:
        """
        Create the initial execution plan for a query.

        Args:
            query: User's query

        Returns:
            ExecutionPlan

        Raises:
            ValueError: If planning fails
        """
        logger.info("Creating initial execution plan")
        plan = await self.planner.create_plan(query)
        logger.info(f"Initial plan created with {len(plan.steps)} steps")
        return plan

    async def _handle_clarification(self, plan: ExecutionPlan) -> dict:
        """
        Handle cases where the planner needs clarification.

        This is a placeholder for clarification handling.
        In a full implementation, this would interact with the user
        to get clarification, then re-plan with the additional information.

        Args:
            plan: Plan with clarification_needed field set

        Returns:
            Dictionary describing the clarification need
        """
        logger.info(f"Clarification needed: {plan.clarification_needed.question}")

        # TODO: Implement full clarification handling
        # This would involve:
        # 1. Presenting the clarification question to the user
        # 2. Collecting their response
        # 3. Re-running create_plan() with the clarification

        return {
            "status": "clarification_needed",
            "clarification": plan.clarification_needed.model_dump(),
            "message": "Please provide clarification and resubmit your query."
        }

    async def _approval_loop(
        self,
        plan: ExecutionPlan,
        query: str,
        workflow_state: ApprovalWorkflowState
    ) -> ExecutionPlan:
        """
        Run the approval loop with support for plan revisions.

        This loop continues until the user approves or rejects the plan.
        If the user requests modifications, the plan is revised and
        presented again.

        Args:
            plan: Initial execution plan
            query: Original user query
            workflow_state: Workflow state tracker

        Returns:
            The approved ExecutionPlan

        Raises:
            WorkflowRejectedError: If user rejects the plan
            ValueError: If plan revision fails
        """
        logger.info("Entering approval loop")

        current_plan = plan
        revision_number = 0

        while workflow_state.current_status not in (
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED
        ):
            revision_number += 1
            logger.info(f"Presenting plan revision {revision_number} for approval")

            # Generate human-friendly summary
            summary = await self.summarizer.summarize_plan(
                plan=current_plan,
                query=query
            )

            # Request approval from user
            feedback = await self.approval_handler.request_approval(
                summary=summary,
                revision_number=revision_number
            )

            # Record this revision
            revision = PlanRevision(
                revision_number=revision_number,
                original_plan=current_plan,
                summary=summary,
                user_feedback=feedback,
                timestamp=datetime.now()
            )
            workflow_state.revisions.append(revision)

            # Handle feedback
            if feedback.status == ApprovalStatus.APPROVED:
                logger.info(f"Plan approved on revision {revision_number}")
                workflow_state.current_status = ApprovalStatus.APPROVED
                workflow_state.final_approved_plan = current_plan
                return current_plan

            elif feedback.status == ApprovalStatus.REJECTED:
                logger.info(f"Plan rejected on revision {revision_number}")
                workflow_state.current_status = ApprovalStatus.REJECTED
                raise WorkflowRejectedError(
                    f"User rejected the plan on revision {revision_number}"
                )

            elif feedback.status == ApprovalStatus.NEEDS_REVISION:
                logger.info(f"User requested revision: {feedback.feedback_text}")

                # Revise the plan based on feedback
                current_plan = await self.planner.revise_plan(
                    original_plan=current_plan,
                    user_feedback=feedback.feedback_text,
                    original_query=query
                )

                logger.info(f"Created revised plan with {len(current_plan.steps)} steps")
                # Loop continues to present the revised plan

            else:
                # Should never happen, but handle gracefully
                logger.error(f"Unexpected approval status: {feedback.status}")
                raise ValueError(f"Invalid approval status: {feedback.status}")

        # Should never reach here, but return the current plan if we do
        return current_plan
