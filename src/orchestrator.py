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
    SufficiencyStatus,
)
from src.agents.planner import PlannerAgent
from src.agents.summarizer import SummarizerAgent
from src.agents.executor import ExecutorAgent
from src.agents.sufficiency import SufficiencyChecker
from src.approval_handler import ApprovalHandler
from src.config import Settings

logger = logging.getLogger(__name__)


class ProspectingOrchestrator:
    """
    Main orchestrator for the prospecting workflow with user approval.

    This orchestrator coordinates the entire prospecting process:
    1. Query planning (with optional clarification)
    2. Plan approval loop (with revision support)
    3. Plan execution
    4. Result validation (sufficiency checking with retry support)
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
        self.executor = ExecutorAgent(settings)
        self.sufficiency_checker = SufficiencyChecker(settings)
        # TODO: Add reporter when implemented

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
            logger.info("Plan approved - starting execution")
            logger.info(f"Executing plan with {len(approved_plan.steps)} steps")

            execution_results = await self.executor.execute_plan(
                plan=approved_plan,
                original_query=query
            )

            logger.info(
                f"Execution complete: {len(execution_results.results)} steps, "
                f"{execution_results.total_records} records, "
                f"{execution_results.execution_time_ms}ms"
            )

            # Step 5: Check sufficiency and handle retries
            max_retries = 1  # Allow one retry attempt
            for retry_attempt in range(max_retries + 1):
                logger.info(f"Evaluating sufficiency (attempt {retry_attempt + 1}/{max_retries + 1})")

                sufficiency = await self.sufficiency_checker.evaluate(execution_results)

                logger.info(
                    f"Sufficiency check: {sufficiency.status.value} "
                    f"({len(sufficiency.gaps)} gaps identified)"
                )

                if sufficiency.status == SufficiencyStatus.SUFFICIENT:
                    # Filter existing clients and return successful result
                    logger.info("Results are sufficient - filtering clients and preparing output")
                    filtered_results = self.sufficiency_checker.filter_existing_clients(execution_results)

                    # TODO: Generate report

                    return {
                        "status": "sufficient",
                        "query": query,
                        "plan": approved_plan.model_dump(),
                        "workflow_state": workflow_state.model_dump(),
                        "execution_results": filtered_results.model_dump(),
                        "sufficiency": {
                            "status": sufficiency.status.value,
                            "reasoning": sufficiency.reasoning,
                            "gaps": sufficiency.gaps
                        },
                        "summary": {
                            "steps_executed": len(filtered_results.results),
                            "steps_succeeded": sum(1 for r in filtered_results.results if r.success),
                            "steps_failed": sum(1 for r in filtered_results.results if not r.success),
                            "total_records": filtered_results.total_records,
                            "companies_found": len(filtered_results.companies),
                            "individuals_found": len(filtered_results.individuals),
                            "execution_time_ms": filtered_results.execution_time_ms,
                            "sources_queried": [s.value for s in filtered_results.sources_queried]
                        }
                    }

                elif sufficiency.status == SufficiencyStatus.CLARIFICATION_NEEDED:
                    # Need user input to proceed
                    logger.info(f"Clarification needed: {sufficiency.clarification.question}")
                    return {
                        "status": "clarification_needed",
                        "query": query,
                        "clarification": sufficiency.clarification.model_dump(),
                        "reasoning": sufficiency.reasoning,
                        "gaps": sufficiency.gaps,
                        "execution_summary": {
                            "steps_executed": len(execution_results.results),
                            "total_records": execution_results.total_records
                        }
                    }

                elif sufficiency.status == SufficiencyStatus.RETRY_NEEDED:
                    # Retry specific steps if we haven't exhausted attempts
                    if retry_attempt < max_retries:
                        logger.info(
                            f"Retrying {len(sufficiency.retry_steps)} steps: {sufficiency.retry_steps}"
                        )
                        execution_results = await self._retry_steps(
                            plan=approved_plan,
                            previous_results=execution_results,
                            retry_step_ids=sufficiency.retry_steps,
                            query=query
                        )
                        # Loop continues to re-evaluate
                    else:
                        # Exhausted retries
                        logger.warning(
                            f"Retry limit reached - returning insufficient results with {len(sufficiency.gaps)} gaps"
                        )
                        return {
                            "status": "insufficient",
                            "query": query,
                            "reasoning": sufficiency.reasoning,
                            "gaps": sufficiency.gaps,
                            "retry_steps_attempted": sufficiency.retry_steps,
                            "execution_results": execution_results.model_dump(),
                            "message": "Unable to gather sufficient data after retries. Please refine your query or check data source availability."
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

    async def _retry_steps(
        self,
        plan: ExecutionPlan,
        previous_results,
        retry_step_ids: list[int],
        query: str
    ):
        """
        Retry execution after failed or incomplete steps.

        Currently re-executes the entire plan. Future enhancement could
        preserve successful results and only re-run failed steps.

        Args:
            plan: The original execution plan
            previous_results: Results from the previous execution attempt
            retry_step_ids: List of step IDs that need retry (informational)
            query: Original query

        Returns:
            New AggregatedResults from retry execution
        """
        logger.info(
            f"Retrying execution (originally failed steps: {retry_step_ids})"
        )

        # Re-execute the entire plan
        # TODO: Optimize to only re-execute failed steps while preserving successful ones
        retry_results = await self.executor.execute_plan(
            plan=plan,
            original_query=query
        )

        logger.info(
            f"Retry complete: {len(retry_results.results)} steps, "
            f"{retry_results.total_records} records"
        )

        return retry_results
