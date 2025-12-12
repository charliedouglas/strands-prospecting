"""
Summarizer Agent for the prospecting system.

This agent converts technical ExecutionPlan objects into user-friendly
PlanSummary objects that can be easily understood by non-technical users.
"""

import json
import logging
from typing import Optional

from strands import Agent
from strands.models import BedrockModel
from pydantic import ValidationError

from src.models import ExecutionPlan, PlanSummary, DataSource
from src.config import Settings

logger = logging.getLogger(__name__)


# Summarizer system prompt
SUMMARIZER_SYSTEM_PROMPT = """You are a plan summarizer for a prospecting research system. Your job is to convert technical execution plans into user-friendly summaries.

You will receive a detailed ExecutionPlan in JSON format containing:
- reasoning: The planner's chain of thought
- steps: Detailed steps with data sources, actions, and parameters
- estimated_sources: Number of unique data sources
- confidence: Planner's confidence score (0-1)

Your task is to create a concise, human-friendly summary that includes:
1. data_sources: List of data source NAMES (not IDs). Map technical IDs to friendly names:
   - orbis → "Orbis (Bureau van Dijk)"
   - wealthx → "Wealth-X"
   - wealth_monitor → "Wealth Monitor"
   - companies_house → "UK Companies House"
   - dun_bradstreet → "Dun & Bradstreet"
   - crunchbase → "Crunchbase"
   - pitchbook → "PitchBook"
   - serpapi → "SerpAPI (News)"
   - internal_crm → "Internal CRM"

2. key_actions: 3-5 bullet points describing what will happen in plain English. Focus on business value, not technical details.

3. reasoning_summary: A 1-2 sentence explanation of the planner's strategy in simple language.

Output ONLY a valid JSON object matching this structure:
{
    "data_sources": ["Friendly Name 1", "Friendly Name 2"],
    "key_actions": [
        "Action 1 in plain English",
        "Action 2 in plain English"
    ],
    "reasoning_summary": "Brief explanation of the strategy"
}

Guidelines:
- Use clear, non-technical language
- Focus on what the user will learn, not how the system works
- Be concise but informative
- Avoid mentioning step IDs, technical parameters, or API details
- Highlight business value (e.g., "Find companies that raised funding" not "Query Crunchbase API")
"""


# Data source ID to friendly name mapping
DATA_SOURCE_NAMES = {
    DataSource.ORBIS: "Orbis (Bureau van Dijk)",
    DataSource.WEALTHX: "Wealth-X",
    DataSource.WEALTH_MONITOR: "Wealth Monitor",
    DataSource.COMPANIES_HOUSE: "UK Companies House",
    DataSource.DUN_BRADSTREET: "Dun & Bradstreet",
    DataSource.CRUNCHBASE: "Crunchbase",
    DataSource.PITCHBOOK: "PitchBook",
    DataSource.SERPAPI: "SerpAPI (News)",
    DataSource.INTERNAL_CRM: "Internal CRM",
}


class SummarizerAgent:
    """
    Agent that generates human-friendly summaries of execution plans.

    Uses Claude Haiku 4.5 for fast, cost-effective summarization.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the summarizer agent.

        Args:
            settings: Application settings containing model configuration
        """
        self.settings = settings

        # Use Haiku 4.5 for cost-effective summarization
        self.model = BedrockModel(
            model_id=settings.executor_model,  # Haiku 4.5
            temperature=0.7,  # Some creativity for natural language
            max_tokens=1000,  # Summaries should be concise
        )

        # Create reusable agent
        self.agent = Agent(
            model=self.model,
            system_prompt=SUMMARIZER_SYSTEM_PROMPT,
        )

        logger.info(f"SummarizerAgent initialized with model: {settings.executor_model}")

    async def summarize_plan(
        self,
        plan: ExecutionPlan,
        query: str
    ) -> PlanSummary:
        """
        Convert an ExecutionPlan to a user-friendly PlanSummary.

        Args:
            plan: The execution plan to summarize
            query: The original user query

        Returns:
            PlanSummary with human-friendly descriptions

        Raises:
            ValueError: If the agent returns invalid JSON or the response cannot be parsed
        """
        logger.info("Generating plan summary")

        try:
            # Create prompt with plan data
            prompt = self._create_summarization_prompt(plan, query)

            # Get summary from agent
            response = await self.agent.invoke_async(prompt)

            # Parse response
            summary_data = self._parse_summary_response(response)

            # Create PlanSummary object
            summary = PlanSummary(
                query=query,
                data_sources=summary_data["data_sources"],
                key_actions=summary_data["key_actions"],
                estimated_sources=plan.estimated_sources,
                confidence=plan.confidence,
                reasoning_summary=summary_data["reasoning_summary"],
            )

            logger.info(f"Successfully generated summary with {len(summary.data_sources)} sources and {len(summary.key_actions)} actions")
            return summary

        except Exception as e:
            logger.error(f"Failed to generate plan summary: {e}")
            # Fall back to basic summary if AI summarization fails
            return self._create_fallback_summary(plan, query)

    def _create_summarization_prompt(self, plan: ExecutionPlan, query: str) -> str:
        """Create the prompt for the summarization agent."""
        plan_json = json.dumps(plan.model_dump(), indent=2)
        return f"""Please summarize this execution plan for the query: "{query}"

ExecutionPlan:
{plan_json}

Return a JSON object with data_sources, key_actions, and reasoning_summary."""

    def _parse_summary_response(self, response: str) -> dict:
        """
        Parse the agent's response into structured data.

        Args:
            response: The agent's text response

        Returns:
            Dictionary with data_sources, key_actions, and reasoning_summary

        Raises:
            ValueError: If response cannot be parsed as valid JSON
        """
        try:
            # Try to extract JSON from the response
            response = response.strip()

            # Remove markdown code blocks if present
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            response = response.strip()

            # Parse JSON
            data = json.loads(response)

            # Validate required fields
            if not isinstance(data.get("data_sources"), list):
                raise ValueError("Missing or invalid 'data_sources' field")
            if not isinstance(data.get("key_actions"), list):
                raise ValueError("Missing or invalid 'key_actions' field")
            if not isinstance(data.get("reasoning_summary"), str):
                raise ValueError("Missing or invalid 'reasoning_summary' field")

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse summary JSON: {e}")
            logger.debug(f"Response was: {response}")
            raise ValueError(f"Invalid JSON response from summarizer: {e}")
        except Exception as e:
            logger.error(f"Error parsing summary response: {e}")
            raise ValueError(f"Failed to parse summary response: {e}")

    def _create_fallback_summary(self, plan: ExecutionPlan, query: str) -> PlanSummary:
        """
        Create a basic summary when AI summarization fails.

        This provides a fallback that extracts information directly from
        the plan structure without using the LLM.

        Args:
            plan: The execution plan
            query: The original user query

        Returns:
            Basic PlanSummary constructed from plan data
        """
        logger.warning("Using fallback summary generation")

        # Extract unique data sources
        unique_sources = set()
        for step in plan.steps:
            unique_sources.add(step.source)

        data_sources = [
            DATA_SOURCE_NAMES.get(source, source.value.title())
            for source in sorted(unique_sources)
        ]

        # Create basic actions from steps
        key_actions = []
        for step in plan.steps[:5]:  # Limit to first 5 steps
            source_name = DATA_SOURCE_NAMES.get(step.source, step.source.value.title())
            action = f"{step.reason} (via {source_name})"
            key_actions.append(action)

        # Use planner's reasoning as summary
        reasoning_summary = plan.reasoning[:200] + "..." if len(plan.reasoning) > 200 else plan.reasoning

        return PlanSummary(
            query=query,
            data_sources=data_sources,
            key_actions=key_actions,
            estimated_sources=plan.estimated_sources,
            confidence=plan.confidence,
            reasoning_summary=reasoning_summary,
        )
