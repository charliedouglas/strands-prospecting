"""
Executor Agent for the prospecting system.

Executes a pre-defined execution plan by calling data source tools
in the correct order and aggregating results.
"""

import logging
import time
import re
from typing import Optional, Callable, Any
from datetime import datetime

from src.models import (
    ExecutionPlan,
    PlanStep,
    SearchResult,
    AggregatedResults,
    DataSource,
)
from src.config import Settings
from src.tools import (
    orbis_search_companies,
    orbis_get_directors,
    orbis_get_ownership,
    crunchbase_search_funding_rounds,
    crunchbase_get_organization,
    pitchbook_search_deals,
    pitchbook_get_company,
    companies_house_search,
    companies_house_get_company,
    companies_house_get_officers,
    companies_house_get_pscs,
    wealthx_search_profiles,
    wealthx_get_profile,
    wealth_monitor_search,
    dnb_match_company,
    dnb_get_company_data,
    serpapi_news_search,
    serpapi_web_search,
    crm_check_clients,
    crm_get_exclusions,
)

logger = logging.getLogger(__name__)


class ExecutorAgent:
    """
    Executor agent that executes execution plans.

    Takes an ExecutionPlan and executes each step by calling the
    appropriate data source tools in order.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the executor agent.

        Args:
            settings: Configuration settings (uses defaults if not provided)
        """
        self.settings = settings or Settings()
        self.tool_map = self._build_tool_map()
        logger.info(f"Initialized ExecutorAgent with {len(self.tool_map)} tools")

    def _build_tool_map(self) -> dict[tuple[str, str], Callable]:
        """
        Build mapping from (datasource, action) to tool functions.

        Returns:
            Dictionary mapping (source, action) tuples to tool functions
        """
        return {
            # Orbis (3 tools)
            ("orbis", "search_companies"): orbis_search_companies,
            ("orbis", "get_directors"): orbis_get_directors,
            ("orbis", "get_ownership"): orbis_get_ownership,

            # Crunchbase (2 tools)
            ("crunchbase", "search_funding"): crunchbase_search_funding_rounds,
            ("crunchbase", "get_organization"): crunchbase_get_organization,

            # PitchBook (2 tools)
            ("pitchbook", "search_deals"): pitchbook_search_deals,
            ("pitchbook", "get_company"): pitchbook_get_company,

            # Companies House (4 tools)
            ("companies_house", "search"): companies_house_search,
            ("companies_house", "get_company"): companies_house_get_company,
            ("companies_house", "get_officers"): companies_house_get_officers,
            ("companies_house", "get_pscs"): companies_house_get_pscs,

            # Wealth-X (2 tools)
            ("wealthx", "search_profiles"): wealthx_search_profiles,
            ("wealthx", "get_profile"): wealthx_get_profile,

            # Wealth Monitor (1 tool)
            ("wealth_monitor", "search"): wealth_monitor_search,

            # Dun & Bradstreet (2 tools)
            ("dun_bradstreet", "match_company"): dnb_match_company,
            ("dun_bradstreet", "get_company_data"): dnb_get_company_data,

            # SerpAPI (2 tools)
            ("serpapi", "news_search"): serpapi_news_search,
            ("serpapi", "web_search"): serpapi_web_search,

            # Internal CRM (2 tools)
            ("internal_crm", "check_clients"): crm_check_clients,
            ("internal_crm", "get_exclusions"): crm_get_exclusions,
        }

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        original_query: str
    ) -> AggregatedResults:
        """
        Execute an execution plan.

        Main entry point. Processes each step in order, resolves
        dependencies, calls tools, and aggregates results.

        Args:
            plan: The execution plan to follow
            original_query: The original user query

        Returns:
            AggregatedResults with all search results and metadata
        """
        logger.info(f"Executing plan with {len(plan.steps)} steps")
        start_time = time.time()

        completed_steps: dict[int, SearchResult] = {}
        all_results: list[SearchResult] = []

        # Execute each step sequentially
        for step in plan.steps:
            logger.info(f"Step {step.step_id}: {step.source.value}.{step.action}")

            # Check dependencies
            if not self._dependencies_met(step, completed_steps):
                error_msg = f"Dependencies not met: {step.depends_on}"
                logger.error(error_msg)
                result = self._create_error_result(step, error_msg, 0)
                all_results.append(result)
                completed_steps[step.step_id] = result
                continue

            # Execute step
            result = await self._execute_step(step, completed_steps)
            all_results.append(result)
            completed_steps[step.step_id] = result

            # Log result
            if result.success:
                logger.info(
                    f"Step {step.step_id} completed: "
                    f"{result.record_count} records in {result.execution_time_ms}ms"
                )
            else:
                logger.error(f"Step {step.step_id} failed: {result.error}")

        # Calculate total time
        total_time_ms = int((time.time() - start_time) * 1000)

        # Build aggregated results
        aggregated = AggregatedResults(
            original_query=original_query,
            plan=plan,
            results=all_results,
            companies=[],  # TODO: Implement deduplication
            individuals=[],  # TODO: Implement deduplication
            total_records=sum(r.record_count for r in all_results),
            sources_queried=list(set(r.source for r in all_results)),
            execution_time_ms=total_time_ms
        )

        logger.info(
            f"Execution complete: {len(all_results)} steps, {total_time_ms}ms total"
        )
        return aggregated

    def _dependencies_met(
        self,
        step: PlanStep,
        completed_steps: dict[int, SearchResult]
    ) -> bool:
        """
        Check if step dependencies have been completed.

        Args:
            step: The step to check
            completed_steps: Dictionary of completed steps by ID

        Returns:
            True if all dependencies are met, False otherwise
        """
        for dep_id in step.depends_on:
            if dep_id not in completed_steps:
                return False
        return True

    async def _execute_step(
        self,
        step: PlanStep,
        completed_steps: dict[int, SearchResult]
    ) -> SearchResult:
        """
        Execute a single plan step.

        Args:
            step: The plan step to execute
            completed_steps: Dictionary of previously completed steps

        Returns:
            SearchResult with execution outcome
        """
        step_start = time.time()

        try:
            # Resolve parameter references
            resolved_params = self._resolve_param_references(
                step.params,
                completed_steps
            )

            # Get tool function
            tool_func = self.tool_map.get((step.source.value, step.action))
            if tool_func is None:
                error_msg = f"No tool found for {step.source.value}.{step.action}"
                logger.error(error_msg)
                return self._create_error_result(step, error_msg, 0)

            # Call tool (all tools are async)
            logger.debug(
                f"Calling {step.source.value}.{step.action} "
                f"with params: {resolved_params}"
            )
            result_data = await tool_func(**resolved_params)

            execution_time_ms = int((time.time() - step_start) * 1000)

            # Check if tool returned error
            if isinstance(result_data, dict) and "error" in result_data:
                return SearchResult(
                    step_id=step.step_id,
                    source=step.source,
                    success=False,
                    data=result_data,
                    error=result_data["error"],
                    record_count=0,
                    execution_time_ms=execution_time_ms,
                    timestamp=datetime.now()
                )

            # Count records
            record_count = self._count_records(result_data)

            # Create success result
            return SearchResult(
                step_id=step.step_id,
                source=step.source,
                success=True,
                data=result_data,
                error=None,
                record_count=record_count,
                execution_time_ms=execution_time_ms,
                timestamp=datetime.now()
            )

        except Exception as e:
            execution_time_ms = int((time.time() - step_start) * 1000)
            logger.error(f"Exception in step {step.step_id}: {e}", exc_info=True)
            return self._create_error_result(step, str(e), execution_time_ms)

    def _resolve_param_references(
        self,
        params: dict,
        completed_steps: dict[int, SearchResult]
    ) -> dict:
        """
        Resolve parameter references like $step_1.company_number.

        Recursively processes parameter dict to replace references
        with actual values from completed steps.

        Args:
            params: Parameter dictionary potentially containing references
            completed_steps: Dictionary of completed steps

        Returns:
            Dictionary with all references resolved
        """
        resolved = {}

        for key, value in params.items():
            if isinstance(value, str):
                resolved[key] = self._resolve_string_reference(value, completed_steps)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_param_references(value, completed_steps)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_string_reference(item, completed_steps)
                    if isinstance(item, str) else item
                    for item in value
                ]
            else:
                resolved[key] = value

        return resolved

    def _resolve_string_reference(
        self,
        value: str,
        completed_steps: dict[int, SearchResult]
    ) -> Any:
        """
        Resolve a single string reference.

        Pattern: $step_{step_id}.{path.to.field}
        Examples:
        - $step_1 → entire result data
        - $step_1.items[0].company_number → specific field

        Args:
            value: String that may contain a reference
            completed_steps: Dictionary of completed steps

        Returns:
            Resolved value or original string if no reference found
        """
        # Regex: $step_{number}.{optional.path}
        pattern = r'\$step_(\d+)(\.[\w\[\]\.]+)?'
        match = re.search(pattern, value)

        if not match:
            return value  # No reference

        step_id = int(match.group(1))
        path = match.group(2)

        # Get completed step
        if step_id not in completed_steps:
            logger.warning(f"Reference to non-existent step {step_id}")
            return None

        step_result = completed_steps[step_id]

        # If step failed, return None
        if not step_result.success or step_result.data is None:
            logger.warning(f"Reference to failed step {step_id}")
            return None

        # If no path, return entire data
        if path is None:
            return step_result.data

        # Navigate the path
        try:
            result = step_result.data
            path = path.lstrip('.')

            # Split by . and [ to handle nested access
            # e.g., "items[0].company_number"
            parts = re.split(r'\.|\[', path)

            for part in parts:
                if not part:
                    continue

                # Handle array index: [0] → 0
                if part.endswith(']'):
                    idx = int(part.rstrip(']'))
                    result = result[idx]
                else:
                    # Dict key access
                    result = result.get(part) if isinstance(result, dict) else None

                if result is None:
                    logger.warning(f"Path {path} not found in step {step_id}")
                    return None

            return result

        except (KeyError, IndexError, TypeError, ValueError) as e:
            logger.warning(f"Error resolving path {path} in step {step_id}: {e}")
            return None

    def _count_records(self, data: Any) -> int:
        """
        Count records in tool response data.

        Different tools return different structures.

        Args:
            data: Response data from tool

        Returns:
            Number of records
        """
        if data is None:
            return 0

        if isinstance(data, list):
            return len(data)

        if isinstance(data, dict):
            # Check common patterns
            if "count" in data:
                return data["count"]
            if "total_results" in data:
                return data["total_results"]
            if "total_count" in data:
                return data["total_count"]
            if "entities" in data:
                return len(data["entities"])
            if "items" in data:
                return len(data["items"])
            if "results" in data:
                return len(data["results"])

            return 1  # Count as 1 record

        return 1

    def _create_error_result(
        self,
        step: PlanStep,
        error_message: str,
        execution_time_ms: int
    ) -> SearchResult:
        """
        Create a SearchResult for a failed step.

        Args:
            step: The plan step that failed
            error_message: Description of the error
            execution_time_ms: Time taken before error occurred

        Returns:
            SearchResult marked as failed
        """
        return SearchResult(
            step_id=step.step_id,
            source=step.source,
            success=False,
            data=None,
            error=error_message,
            record_count=0,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now()
        )
