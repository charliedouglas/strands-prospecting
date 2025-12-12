"""
Planner Agent for the prospecting system.

This agent analyzes user queries and creates structured execution plans
that specify which data sources to query and in what order.
"""

import json
import logging
from typing import Optional
from enum import Enum

from strands import Agent
from strands.models import BedrockModel
from strands.types.content import SystemContentBlock
from pydantic import ValidationError
from botocore.exceptions import ClientError as BotocoreClientError

from src.models import (
    ExecutionPlan,
    PlanStep,
    ClarificationRequest,
    DataSource,
)
from src.config import Settings

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    """Types of prospecting queries."""
    FUNDING_INVESTMENT = "funding_investment"
    UHNW_INDIVIDUAL = "uhnw_individual"
    UK_COMPANY_STRUCTURE = "uk_company_structure"
    DIRECTORS_FOUNDERS = "directors_founders"
    CREDIT_RISK = "credit_risk"
    NEWS_SIGNALS = "news_signals"
    AMBIGUOUS = "ambiguous"


# Planner system prompt from CLAUDE.md
PLANNER_SYSTEM_PROMPT = """You are a prospecting research planner for a private bank. Your job is to analyze prospecting queries and create structured execution plans.

Available data sources with their EXACT action names and parameters:

- ORBIS (source: "orbis")
  * search_companies
    Parameters: name, country, city, bvd_id, national_id, status, min_revenue, max_revenue, min_employees, max_employees, limit
  * get_directors
    Parameters: bvd_id
  * get_ownership
    Parameters: bvd_id

- CRUNCHBASE (source: "crunchbase")
  * search_funding
    Parameters: investment_type, location, announced_on_gte, announced_on_lte, min_amount_usd, limit
  * get_organization
    Parameters: permalink

- PITCHBOOK (source: "pitchbook")
  * search_deals
    Parameters: deal_type, regions, countries, industries, deal_size_min, deal_size_max, deal_date_min, series, limit
  * get_company
    Parameters: company_id

- COMPANIES_HOUSE (source: "companies_house")
  * search
    Parameters: query, limit
  * get_company
    Parameters: company_number
  * get_officers
    Parameters: company_number
  * get_pscs
    Parameters: company_number

- WEALTHX (source: "wealthx")
  * search_profiles
    Parameters: net_worth_min, countries, industries, interests, keywords, limit
  * get_profile
    Parameters: wealthx_id

- WEALTH_MONITOR (source: "wealth_monitor")
  * search
    Parameters: name, region, min_net_worth, include_property, include_shareholdings

- DUN_BRADSTREET (source: "dun_bradstreet")
  * match_company
    Parameters: name, country, city
  * get_company_data
    Parameters: duns_number

- SERPAPI (source: "serpapi")
  * news_search
    Parameters: query, gl
  * web_search
    Parameters: query

- INTERNAL_CRM (source: "internal_crm")
  * check_clients
    Parameters: individuals, companies
  * get_exclusions
    Parameters: (none)

CRITICAL: You MUST use the EXACT action names and parameter names listed above. Do not invent new action names or parameter names.

When creating a plan:
1. Parse the query to understand what information is needed
2. Identify which data sources can provide that information
3. Use ONLY the action names listed above for each source
4. Determine the optimal order (dependencies matter - e.g., find companies before looking up directors)
5. Consider cross-referencing for accuracy (e.g., both Crunchbase AND PitchBook for funding)
6. ALWAYS include INTERNAL_CRM as the final step to filter out existing clients

If the query is ambiguous or missing critical information, request clarification instead of guessing.

Output a structured ExecutionPlan with:
- reasoning: Your chain of thought
- steps: Ordered list of data source queries with specific parameters and EXACT action names
- clarification_needed: Only if the query is too ambiguous to proceed
- confidence: Your confidence in this plan (0-1)

You must respond with valid JSON matching the ExecutionPlan schema."""


def get_primary_sources_for_intent(intent: QueryIntent) -> list[DataSource]:
    """
    Get primary data sources for a given query intent.

    Based on the Data Source Selection Logic table from CLAUDE.md.

    Args:
        intent: The identified query intent

    Returns:
        List of primary data sources to query
    """
    intent_to_sources = {
        QueryIntent.FUNDING_INVESTMENT: [
            DataSource.CRUNCHBASE,
            DataSource.PITCHBOOK,
        ],
        QueryIntent.UHNW_INDIVIDUAL: [
            DataSource.WEALTHX,
            DataSource.WEALTH_MONITOR,
        ],
        QueryIntent.UK_COMPANY_STRUCTURE: [
            DataSource.ORBIS,
            DataSource.COMPANIES_HOUSE,
        ],
        QueryIntent.DIRECTORS_FOUNDERS: [
            DataSource.COMPANIES_HOUSE,
            DataSource.ORBIS,
        ],
        QueryIntent.CREDIT_RISK: [
            DataSource.DUN_BRADSTREET,
        ],
        QueryIntent.NEWS_SIGNALS: [
            DataSource.SERPAPI,
        ],
    }

    return intent_to_sources.get(intent, [])


def get_secondary_sources_for_intent(intent: QueryIntent) -> list[DataSource]:
    """
    Get secondary/supporting data sources for a given query intent.

    Args:
        intent: The identified query intent

    Returns:
        List of secondary data sources that can supplement the primary sources
    """
    intent_to_sources = {
        QueryIntent.FUNDING_INVESTMENT: [
            DataSource.SERPAPI,  # news
            DataSource.ORBIS,
        ],
        QueryIntent.UHNW_INDIVIDUAL: [
            DataSource.COMPANIES_HOUSE,  # directorships
        ],
        QueryIntent.UK_COMPANY_STRUCTURE: [
            DataSource.DUN_BRADSTREET,
        ],
        QueryIntent.DIRECTORS_FOUNDERS: [
            DataSource.WEALTHX,
            DataSource.PITCHBOOK,
        ],
        QueryIntent.CREDIT_RISK: [
            DataSource.ORBIS,
        ],
    }

    return intent_to_sources.get(intent, [])


class PlannerAgent:
    """
    Planner agent that creates execution plans from user queries.

    Uses Claude Sonnet 4.5 with extended thinking to analyze queries
    and determine which data sources to query.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the planner agent.

        Args:
            settings: Configuration settings (uses defaults if not provided)
        """
        self.settings = settings or Settings()

        # Create BedrockModel for planner with extended thinking
        planner_config = {
            "model_id": self.settings.planner_model,
        }

        # Add extended thinking if enabled
        if self.settings.enable_extended_thinking:
            # When extended thinking is enabled, temperature MUST be 1.0
            planner_config["temperature"] = 1.0
            # max_tokens must be GREATER than thinking.budget_tokens
            # Set to budget_tokens + response tokens (4000)
            planner_config["max_tokens"] = self.settings.thinking_budget_tokens + 4000
            planner_config["additional_request_fields"] = {
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": self.settings.thinking_budget_tokens
                }
            }
        else:
            # Lower temperature for more consistent planning when not using extended thinking
            planner_config["temperature"] = 0.3
            planner_config["max_tokens"] = 4000

        # Note: Prompt caching with Bedrock has API limitations with extended thinking
        # For now, we prioritize extended thinking over caching
        # TODO: Re-evaluate caching strategy when API supports both features together

        self.planner_model = BedrockModel(**planner_config)

        # Create the planner agent once (reused for all planning requests)
        self.planner_agent = Agent(
            model=self.planner_model,
            system_prompt=PLANNER_SYSTEM_PROMPT,
            name="planner",
        )

        # Create intent classifier agent once (reused for all intent classifications)
        self.intent_agent = Agent(
            model=self.settings.executor_model,
            system_prompt="You are an intent classifier for prospecting queries. Respond only with the intent category name.",
            name="intent_classifier",
        )

        logger.info(
            f"Initialized PlannerAgent with model {self.settings.planner_model} "
            f"(extended_thinking={'enabled' if self.settings.enable_extended_thinking else 'disabled'})"
        )

    async def create_plan(self, query: str) -> ExecutionPlan:
        """
        Create an execution plan for a prospecting query.

        This is the main entry point for the planner agent. It analyzes
        the query and returns a structured plan.

        Args:
            query: The user's prospecting query

        Returns:
            ExecutionPlan with steps, reasoning, and optional clarification

        Raises:
            ValueError: If the model fails to produce a valid plan after retries
        """
        logger.info(f"Creating plan for query: {query}")

        # Create the prompt for the model
        prompt = self._create_planning_prompt(query)

        # Try to get a valid plan (with retry logic)
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.debug(f"Planning attempt {attempt + 1}/{max_retries}")

                # Reuse the planner agent created during initialization
                response = await self.planner_agent.invoke_async(prompt)

                # Extract the plan from the response
                plan = self._parse_plan_from_response(response)

                logger.info(f"Successfully created plan with {len(plan.steps)} steps")
                return plan

            except (ValidationError, json.JSONDecodeError, ValueError, BotocoreClientError) as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

                # Add feedback to the prompt for retry
                if attempt < max_retries - 1:
                    prompt = self._create_retry_prompt(query, str(e))

        # All retries exhausted
        logger.error(f"Failed to create valid plan after {max_retries} attempts: {last_error}")
        raise ValueError(f"Failed to create valid plan: {last_error}")

    def _create_planning_prompt(self, query: str) -> str:
        """
        Create the initial planning prompt for the model.

        Args:
            query: User's query

        Returns:
            Formatted prompt string
        """
        return f"""Analyze this prospecting query and create an execution plan:

Query: "{query}"

Respond with a JSON object matching this ExecutionPlan schema:
{{
  "reasoning": "Your chain of thought explaining the strategy",
  "steps": [
    {{
      "step_id": 1,
      "source": "data_source_name",
      "action": "exact_action_name_from_system_prompt",
      "params": {{"param": "value"}},
      "reason": "Why this step is needed",
      "depends_on": []
    }}
  ],
  "clarification_needed": null or {{
    "question": "What needs clarification?",
    "options": ["option1", "option2"],
    "context": "Why clarification is needed"
  }},
  "estimated_sources": number,
  "confidence": 0.0-1.0
}}

Valid sources, actions, and parameters (use EXACT names):

ORBIS:
- search_companies: name, country, city, bvd_id, national_id, status, min_revenue, max_revenue, min_employees, max_employees, limit
- get_directors: bvd_id
- get_ownership: bvd_id

CRUNCHBASE:
- search_funding: investment_type, location, announced_on_gte, announced_on_lte, min_amount_usd, limit
- get_organization: permalink

PITCHBOOK:
- search_deals: deal_type, regions, countries, industries, deal_size_min, deal_size_max, deal_date_min, series, limit
- get_company: company_id

COMPANIES_HOUSE:
- search: query, limit
- get_company: company_number
- get_officers: company_number
- get_pscs: company_number

WEALTHX:
- search_profiles: net_worth_min, countries, industries, interests, keywords, limit
- get_profile: wealthx_id

WEALTH_MONITOR:
- search: name, region, min_net_worth, include_property, include_shareholdings

DUN_BRADSTREET:
- match_company: name, country, city
- get_company_data: duns_number

SERPAPI:
- news_search: query, gl
- web_search: query

INTERNAL_CRM:
- check_clients: individuals, companies
- get_exclusions: (no parameters)

Remember:
- USE EXACT action and parameter names from the list above
- Always include internal_crm as the final step
- Order steps by dependencies
- Request clarification if the query is too vague

Respond ONLY with the JSON object, no additional text."""

    def _create_retry_prompt(self, query: str, error: str) -> str:
        """
        Create a retry prompt with feedback about the previous error.

        Args:
            query: Original user query
            error: Error message from previous attempt

        Returns:
            Formatted retry prompt
        """
        return f"""The previous plan had an error: {error}

Please try again with a valid ExecutionPlan JSON for this query:

Query: "{query}"

Ensure:
1. All fields are present (reasoning, steps, clarification_needed, estimated_sources, confidence)
2. step_id values are sequential integers starting from 1
3. source values use valid lowercase data source names
4. Use EXACT action names and parameter names from the system prompt
5. Common action names: search_companies, get_directors, get_ownership, search_funding, get_organization, search_deals, get_company, search, get_officers, get_pscs, search_profiles, get_profile, match_company, get_company_data, news_search, web_search, check_clients, get_exclusions
6. Common parameter names: query, limit, name, country, investment_type, location, announced_on_gte, deal_type, regions, countries, company_number, net_worth_min, etc.
7. confidence is a float between 0.0 and 1.0
8. The JSON is properly formatted

Respond ONLY with valid JSON."""

    def _parse_plan_from_response(self, response: str) -> ExecutionPlan:
        """
        Parse an ExecutionPlan from the model's response.

        Args:
            response: Raw response from the model

        Returns:
            Validated ExecutionPlan object

        Raises:
            ValueError: If response cannot be parsed or validated
            ValidationError: If the plan doesn't match the schema
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
            plan_dict = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in response: {e}")

        # Validate and create ExecutionPlan
        try:
            plan = ExecutionPlan(**plan_dict)
        except ValidationError as e:
            raise ValidationError(f"Plan validation failed: {e}")

        return plan

    async def analyze_query_intent(self, query: str) -> QueryIntent:
        """
        Analyze a query to determine its primary intent using LLM.

        This is a helper method for understanding what the user is asking for.
        Uses Claude to classify the query intent based on semantic understanding.

        Args:
            query: User's query

        Returns:
            QueryIntent enum value
        """
        logger.debug(f"Analyzing intent for query: {query}")

        # Create intent classification prompt
        intent_prompt = f"""Analyze this prospecting query and classify its primary intent.

Query: "{query}"

Available intent categories:
- funding_investment: Queries about funding rounds, investments, VC/PE deals
- uhnw_individual: Queries about wealthy individuals, high net worth persons
- uk_company_structure: Queries about company ownership, structure, subsidiaries
- directors_founders: Queries about company directors, founders, executives, management
- credit_risk: Queries about credit ratings, financial health, risk assessment
- news_signals: Queries about recent news, announcements, events
- ambiguous: Query is too vague or doesn't fit the above categories

Respond with ONLY the intent category name (e.g., "funding_investment"), nothing else."""

        try:
            # Reuse the intent agent created during initialization
            response = await self.intent_agent.invoke_async(intent_prompt)
            intent_str = str(response).strip().lower()

            # Parse the intent
            for intent in QueryIntent:
                if intent.value in intent_str or intent.name.lower() in intent_str:
                    logger.info(f"Query intent classified as: {intent.value}")
                    return intent

            # If no match found, default to ambiguous
            logger.warning(f"Could not parse intent from response: {intent_str}")
            return QueryIntent.AMBIGUOUS

        except (BotocoreClientError, ValueError) as e:
            logger.error(f"Error classifying intent: {e}")
            # Fallback to ambiguous on error
            return QueryIntent.AMBIGUOUS

    async def revise_plan(
        self,
        original_plan: ExecutionPlan,
        user_feedback: str,
        original_query: str
    ) -> ExecutionPlan:
        """
        Revise an execution plan based on user feedback.

        This method takes an existing plan and user feedback, then creates
        a revised plan that addresses the user's concerns while maintaining
        the overall strategy.

        Args:
            original_plan: The plan that needs revision
            user_feedback: User's feedback explaining what they want changed
            original_query: The original user query (for context)

        Returns:
            Revised ExecutionPlan

        Raises:
            ValueError: If the model fails to produce a valid revised plan
        """
        logger.info(f"Revising plan based on user feedback: {user_feedback}")

        # Create revision prompt
        revision_prompt = self._create_revision_prompt(
            original_plan,
            user_feedback,
            original_query
        )

        # Try to get a valid revised plan (with retry logic)
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.debug(f"Revision attempt {attempt + 1}/{max_retries}")

                # Reuse the planner agent
                response = await self.planner_agent.invoke_async(revision_prompt)

                # Extract the revised plan
                revised_plan = self._parse_plan_from_response(response)

                logger.info(f"Successfully revised plan with {len(revised_plan.steps)} steps")
                return revised_plan

            except (ValidationError, json.JSONDecodeError, ValueError, BotocoreClientError) as e:
                last_error = e
                logger.warning(f"Revision attempt {attempt + 1} failed: {e}")

                # Add feedback for retry
                if attempt < max_retries - 1:
                    revision_prompt = self._create_revision_retry_prompt(
                        original_query,
                        user_feedback,
                        str(e)
                    )

        # All retries exhausted
        logger.error(f"Failed to revise plan after {max_retries} attempts: {last_error}")
        raise ValueError(f"Failed to revise plan: {last_error}")

    def _create_revision_prompt(
        self,
        original_plan: ExecutionPlan,
        user_feedback: str,
        original_query: str
    ) -> str:
        """
        Create a prompt for revising an execution plan.

        Args:
            original_plan: The original plan
            user_feedback: User's feedback
            original_query: Original user query

        Returns:
            Formatted revision prompt
        """
        plan_json = json.dumps(original_plan.model_dump(), indent=2)

        return f"""You previously created this execution plan for the query: "{original_query}"

Original Plan:
{plan_json}

The user reviewed this plan and provided feedback:
"{user_feedback}"

Please create a REVISED execution plan that:
1. Addresses the user's feedback
2. Maintains the original query intent
3. Keeps logical step ordering with proper dependencies
4. Uses EXACT action names from the allowed list
5. ALWAYS includes internal_crm as the final step
6. Preserves any steps that work well from the original plan

Return a complete ExecutionPlan in JSON format with all required fields:
- reasoning (explain what changed and why)
- steps (with sequential step_id starting from 1 and EXACT action names)
- clarification_needed (null unless you need more info)
- estimated_sources
- confidence

Valid sources, actions, and parameters (use EXACT names):

ORBIS:
- search_companies: name, country, city, bvd_id, national_id, status, min_revenue, max_revenue, min_employees, max_employees, limit
- get_directors: bvd_id
- get_ownership: bvd_id

CRUNCHBASE:
- search_funding: investment_type, location, announced_on_gte, announced_on_lte, min_amount_usd, limit
- get_organization: permalink

PITCHBOOK:
- search_deals: deal_type, regions, countries, industries, deal_size_min, deal_size_max, deal_date_min, series, limit
- get_company: company_id

COMPANIES_HOUSE:
- search: query, limit
- get_company: company_number
- get_officers: company_number
- get_pscs: company_number

WEALTHX:
- search_profiles: net_worth_min, countries, industries, interests, keywords, limit
- get_profile: wealthx_id

WEALTH_MONITOR:
- search: name, region, min_net_worth, include_property, include_shareholdings

DUN_BRADSTREET:
- match_company: name, country, city
- get_company_data: duns_number

SERPAPI:
- news_search: query, gl
- web_search: query

INTERNAL_CRM:
- check_clients: individuals, companies
- get_exclusions: (no parameters)

Respond ONLY with the JSON object, no additional text."""

    def _create_revision_retry_prompt(
        self,
        original_query: str,
        user_feedback: str,
        error: str
    ) -> str:
        """
        Create a retry prompt for plan revision.

        Args:
            original_query: Original user query
            user_feedback: User's feedback
            error: Error from previous attempt

        Returns:
            Formatted retry prompt
        """
        return f"""The previous revised plan had an error: {error}

Please try again to create a revised plan for:
- Original Query: "{original_query}"
- User Feedback: "{user_feedback}"

Ensure:
1. All fields are present (reasoning, steps, clarification_needed, estimated_sources, confidence)
2. step_id values are sequential integers starting from 1
3. source values use valid lowercase data source names
4. Use EXACT action names and parameter names from the system prompt
5. Common action names: search_companies, get_directors, get_ownership, search_funding, get_organization, search_deals, get_company, search, get_officers, get_pscs, search_profiles, get_profile, match_company, get_company_data, news_search, web_search, check_clients, get_exclusions
6. Common parameter names: query, limit, name, country, investment_type, location, announced_on_gte, deal_type, regions, countries, company_number, net_worth_min, etc.
7. confidence is a float between 0.0 and 1.0
8. The JSON is properly formatted
9. internal_crm is the final step

Respond ONLY with valid JSON."""
