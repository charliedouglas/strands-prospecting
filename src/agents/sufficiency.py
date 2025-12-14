"""
Sufficiency Checker Agent for the prospecting system.

This agent evaluates whether gathered data adequately answers the
original prospecting query and determines next steps.
"""

import json
import logging
from typing import Optional

from strands import Agent
from strands.models import BedrockModel
from pydantic import ValidationError
from botocore.exceptions import ClientError as BotocoreClientError

from src.models import (
    AggregatedResults,
    SufficiencyResult,
    SufficiencyStatus,
)
from src.config import Settings

logger = logging.getLogger(__name__)


# Sufficiency checker system prompt from CLAUDE.md
SUFFICIENCY_CHECKER_SYSTEM_PROMPT = """You are a quality assurance agent for prospecting research. Your job is to evaluate whether the gathered data adequately answers the original query.

Evaluate:
1. Does the data answer the original question?
2. Are there critical gaps? (e.g., asked for founders but only got company data)
3. Is the data internally consistent across sources?
4. Should any results be excluded (existing clients, compliance concerns)?

Return one of:
- SUFFICIENT: Data answers the query, proceed to report generation
- CLARIFICATION_NEEDED: Need user input to refine the search
- RETRY_NEEDED: Should re-run certain steps with modified parameters

Include reasoning for your decision.

You must respond with valid JSON matching the SufficiencyResult schema:
{
  "status": "sufficient" | "clarification_needed" | "retry_needed",
  "reasoning": "Detailed explanation of your evaluation",
  "gaps": ["list", "of", "gaps"],
  "clarification": {
    "question": "What needs clarification?",
    "options": ["option1", "option2"],
    "context": "Why clarification is needed",
    "allow_custom_input": true,
    "custom_input_label": "Other (please specify)"
  } or null,
  "retry_steps": [step_ids to retry],
  "filtered_results": null
}

Note: When providing clarification options, you can set "allow_custom_input": true to include
a final option for free-form user input. Customize "custom_input_label" for context-specific wording.

When evaluating results:

SUFFICIENT criteria:
- Original query is fully answered by the data
- All required entities (companies/individuals) are found
- No critical gaps in requested information
- Cross-source data is consistent
- Existing clients have been properly identified
- At least some non-client prospects remain after filtering

CLARIFICATION_NEEDED criteria:
- All results are existing clients (need different search criteria)
- Query intent is unclear after seeing initial results
- Multiple interpretation paths exist and user must choose
- Results suggest the query needs refinement

RETRY_NEEDED criteria:
- Some steps failed due to transient errors (retryable)
- Parameters can be adjusted to get better results
- Missing data that could be obtained with different parameters
- Data sources returned empty but query is still valid

Critical gaps examples:
- Asked for "founders" but only have company names
- Asked for "funding" but no investor or amount data
- Asked for "UK companies" but got international results
- Asked for "wealth profiles" but only have basic company data

Data consistency checks:
- Same company appears with different names/IDs
- Conflicting financial data across sources
- Date mismatches (e.g., funding rounds)
- Missing expected cross-references (e.g., director not found in Companies House)

Client filtering:
- Check if CRM results indicate existing clients
- Flag prospects that should be excluded
- Distinguish between clients, prospects, and exclusions
- If ALL results are existing clients, request CLARIFICATION_NEEDED"""


class SufficiencyChecker:
    """
    Sufficiency checker agent that evaluates result quality.

    Uses Claude Sonnet 4.5 with extended thinking to deeply analyze
    whether results adequately answer the original query.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the sufficiency checker agent.

        Args:
            settings: Configuration settings (uses defaults if not provided)
        """
        self.settings = settings or Settings()

        # Create BedrockModel for sufficiency checker with extended thinking
        checker_config = {
            "model_id": self.settings.planner_model,  # Use same model as planner (Sonnet 4.5)
        }

        # Add extended thinking if enabled
        if self.settings.enable_extended_thinking:
            # When extended thinking is enabled, temperature MUST be 1.0
            checker_config["temperature"] = 1.0
            # max_tokens must be GREATER than thinking.budget_tokens
            # Set to budget_tokens + response tokens (4000)
            checker_config["max_tokens"] = self.settings.thinking_budget_tokens + 4000
            checker_config["additional_request_fields"] = {
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": self.settings.thinking_budget_tokens
                }
            }
        else:
            # Lower temperature for more consistent evaluation when not using extended thinking
            checker_config["temperature"] = 0.3
            checker_config["max_tokens"] = 4000

        self.checker_model = BedrockModel(**checker_config)

        # Create the sufficiency checker agent (reused for all evaluations)
        self.checker_agent = Agent(
            model=self.checker_model,
            system_prompt=SUFFICIENCY_CHECKER_SYSTEM_PROMPT,
            name="sufficiency_checker",
        )

        logger.info(
            f"Initialized SufficiencyChecker with model {self.settings.planner_model} "
            f"(extended_thinking={'enabled' if self.settings.enable_extended_thinking else 'disabled'})"
        )

    async def evaluate(
        self,
        results: AggregatedResults
    ) -> SufficiencyResult:
        """
        Evaluate whether results sufficiently answer the query.

        This is the main entry point for sufficiency checking. It analyzes
        the aggregated results and determines if they adequately answer
        the original query.

        Args:
            results: Aggregated results from executor

        Returns:
            SufficiencyResult with evaluation status and recommendations

        Raises:
            ValueError: If evaluation fails after retries
        """
        logger.info(f"Evaluating sufficiency for query: {results.original_query}")

        # Create the evaluation prompt
        prompt = self._create_evaluation_prompt(results)

        # Try to get a valid evaluation (with retry logic)
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.debug(f"Evaluation attempt {attempt + 1}/{max_retries}")

                # Use the checker agent
                response = await self.checker_agent.invoke_async(prompt)

                # Parse the sufficiency result
                sufficiency = self._parse_sufficiency_from_response(response)

                logger.info(
                    f"Evaluation complete: {sufficiency.status.value} "
                    f"(gaps: {len(sufficiency.gaps)})"
                )
                return sufficiency

            except (ValidationError, json.JSONDecodeError, ValueError, BotocoreClientError) as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

                # Add feedback for retry
                if attempt < max_retries - 1:
                    prompt = self._create_retry_prompt(results, str(e))

        # All retries exhausted
        logger.error(f"Failed to evaluate sufficiency after {max_retries} attempts: {last_error}")
        raise ValueError(f"Failed to evaluate sufficiency: {last_error}")

    def _create_evaluation_prompt(self, results: AggregatedResults) -> str:
        """
        Create the evaluation prompt for the model.

        Args:
            results: Aggregated results to evaluate

        Returns:
            Formatted prompt string
        """
        # Prepare a summary of results for the prompt
        results_summary = self._summarize_results(results)

        return f"""Evaluate whether these results adequately answer the original prospecting query.

Original Query: "{results.original_query}"

Execution Plan Summary:
- Total steps: {len(results.plan.steps)}
- Sources queried: {[s.value for s in results.sources_queried]}
- Plan reasoning: {results.plan.reasoning}

Results Summary:
{results_summary}

Companies Found: {len(results.companies)}
Individuals Found: {len(results.individuals)}
Total Records: {results.total_records}

Respond with a JSON object matching the SufficiencyResult schema:
{{
  "status": "sufficient" | "clarification_needed" | "retry_needed",
  "reasoning": "Your detailed evaluation explaining the decision",
  "gaps": ["identified", "gaps"],
  "clarification": {{
    "question": "What needs clarification?",
    "options": ["option1", "option2", "option3"],
    "context": "Why clarification is needed",
    "allow_custom_input": true,
    "custom_input_label": "Other (please specify your preference)"
  }} or null,
  "retry_steps": [step_ids],
  "filtered_results": null
}}

Evaluate:
1. Does the data answer the original question?
2. Are there critical gaps in the information?
3. Is the data internally consistent?
4. Have existing clients been properly identified and should be filtered?
5. Are there enough non-client prospects after filtering?

Remember:
- SUFFICIENT: Query is fully answered, proceed to report
- CLARIFICATION_NEEDED: Need user input (e.g., all results are clients, query is ambiguous)
  * When requesting clarification, provide specific options for common scenarios
  * Set "allow_custom_input": true to include a final "Other" option for custom user text
  * Customize "custom_input_label" to match the context (e.g., "Other industry", "Different criteria")
- RETRY_NEEDED: Can improve results by retrying specific steps

Respond ONLY with the JSON object, no additional text."""

    def _create_retry_prompt(self, results: AggregatedResults, error: str) -> str:
        """
        Create a retry prompt with feedback about the previous error.

        Args:
            results: Aggregated results being evaluated
            error: Error message from previous attempt

        Returns:
            Formatted retry prompt
        """
        return f"""The previous evaluation had an error: {error}

Please try again to evaluate these results for the query: "{results.original_query}"

Ensure:
1. status is one of: "sufficient", "clarification_needed", "retry_needed"
2. reasoning is a detailed string explanation
3. gaps is a list of strings
4. clarification is either null or an object with question, options, context
5. retry_steps is a list of integers (step IDs)
6. filtered_results is null (filtering happens after evaluation)
7. The JSON is properly formatted

Respond ONLY with valid JSON matching the SufficiencyResult schema."""

    def _parse_sufficiency_from_response(self, response: str) -> SufficiencyResult:
        """
        Parse a SufficiencyResult from the model's response.

        Args:
            response: Raw response from the model

        Returns:
            Validated SufficiencyResult object

        Raises:
            ValueError: If response cannot be parsed or validated
            ValidationError: If the result doesn't match the schema
        """
        # The response might contain thinking tags or other text
        # Try to extract JSON from the response
        response_text = str(response).strip()

        # Look for JSON object in the response
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')

        if start_idx == -1 or end_idx == -1:
            raise ValueError("No JSON object found in response")

        json_str = response_text[start_idx:end_idx + 1]

        # Parse JSON
        try:
            result_dict = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in response: {e}")

        # Handle null values for list fields (model sometimes returns null instead of [])
        if result_dict.get("retry_steps") is None:
            result_dict["retry_steps"] = []
        if result_dict.get("gaps") is None:
            result_dict["gaps"] = []

        # Validate and create SufficiencyResult
        try:
            sufficiency = SufficiencyResult(**result_dict)
        except ValidationError as e:
            raise ValueError(f"Sufficiency result validation failed: {e}")

        return sufficiency

    def _summarize_results(self, results: AggregatedResults) -> str:
        """
        Create a human-readable summary of results for the prompt.

        Args:
            results: Aggregated results to summarize

        Returns:
            Formatted summary string
        """
        summary_lines = []

        for result in results.results:
            status = "SUCCESS" if result.success else "FAILED"
            summary_lines.append(
                f"Step {result.step_id} ({result.source.value}): "
                f"{status} - {result.record_count} records"
            )
            if result.error:
                summary_lines.append(f"  Error: {result.error}")

        return "\n".join(summary_lines)

    def filter_existing_clients(
        self,
        results: AggregatedResults
    ) -> AggregatedResults:
        """
        Filter out existing clients from the results.

        Examines CRM results and removes any companies or individuals
        that are marked as existing clients.

        Args:
            results: Original aggregated results

        Returns:
            New AggregatedResults with clients filtered out
        """
        logger.info("Filtering existing clients from results")

        # Find CRM check results
        crm_result = None
        for result in results.results:
            if result.source.value == "internal_crm" and result.success:
                crm_result = result
                break

        if not crm_result or not crm_result.data:
            logger.info("No CRM data found, returning original results")
            return results

        # Extract client information from CRM data
        existing_client_names = set()
        excluded_names = set()

        crm_data = crm_result.data
        if isinstance(crm_data, dict):
            # Check individuals
            if "matches" in crm_data and "individuals" in crm_data["matches"]:
                for individual in crm_data["matches"]["individuals"]:
                    if individual.get("is_client"):
                        existing_client_names.add(individual.get("query_name", "").lower())
                    if individual.get("is_excluded"):
                        excluded_names.add(individual.get("query_name", "").lower())

            # Check companies
            if "matches" in crm_data and "companies" in crm_data["matches"]:
                for company in crm_data["matches"]["companies"]:
                    if company.get("is_client"):
                        existing_client_names.add(company.get("query_name", "").lower())
                    if company.get("is_excluded"):
                        excluded_names.add(company.get("query_name", "").lower())

        # Filter companies
        filtered_companies = [
            company for company in results.companies
            if company.name.lower() not in existing_client_names
            and company.name.lower() not in excluded_names
        ]

        # Filter individuals
        filtered_individuals = []
        for individual in results.individuals:
            name = individual.name.lower()
            if name not in existing_client_names and name not in excluded_names:
                # Mark if they're an existing client (for transparency)
                individual.is_existing_client = name in existing_client_names
                filtered_individuals.append(individual)

        # Create filtered results
        filtered = AggregatedResults(
            original_query=results.original_query,
            plan=results.plan,
            results=results.results,
            companies=filtered_companies,
            individuals=filtered_individuals,
            total_records=results.total_records,
            sources_queried=results.sources_queried,
            execution_time_ms=results.execution_time_ms
        )

        logger.info(
            f"Filtered results: "
            f"{len(results.companies)} -> {len(filtered_companies)} companies, "
            f"{len(results.individuals)} -> {len(filtered_individuals)} individuals"
        )

        return filtered
