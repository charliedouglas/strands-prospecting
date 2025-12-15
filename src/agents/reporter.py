"""
Report Generator Agent for the prospecting system.

This agent generates formatted Markdown reports from aggregated
prospecting results, synthesizing data from multiple sources.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from strands import Agent
from strands.models import BedrockModel
from pydantic import BaseModel, Field
from botocore.exceptions import ClientError as BotocoreClientError

from src.models import AggregatedResults, DataSource
from src.config import Settings

logger = logging.getLogger(__name__)


class ProspectingReport(BaseModel):
    """
    Generated prospecting report.

    Contains the formatted Markdown content along with metadata
    about the report generation.
    """
    query_summary: str = Field(..., description="Short summary of the original query")
    generated_at: datetime = Field(default_factory=datetime.now, description="When the report was generated")
    sources_used: list[str] = Field(default_factory=list, description="Data sources that contributed to the report")
    markdown_content: str = Field(..., description="Full Markdown report content")
    companies_count: int = Field(0, description="Number of companies in the report")
    individuals_count: int = Field(0, description="Number of individuals in the report")


# Report generator system prompt
REPORTER_SYSTEM_PROMPT = """You are an expert report writer for a private bank's prospecting team. Your job is to synthesize data from multiple sources into a clear, actionable prospecting report.

Your reports should:
1. Be concise but comprehensive
2. Highlight the most relevant information for business development
3. Synthesize data across sources (not just list raw results)
4. Note data confidence and freshness where relevant
5. Identify key opportunities and recommended next steps
6. Use professional, objective language

Report Structure:
- Executive Summary: 2-3 sentences capturing key findings
- Companies: Overview, financials, funding, key people
- Individuals: Roles, wealth profile, interests, client status
- Recent News: Relevant signals and events
- Data Quality Notes: Gaps, caveats, cross-reference issues
- Recommended Next Steps: Actionable suggestions

When writing:
- Prioritize information relevant to the original query
- Highlight wealth indicators and business opportunities
- Flag any compliance concerns or exclusions
- Use formatting (bold, bullets) for scannability
- Include source attribution where relevant

You must respond with a well-structured Markdown report."""


class ReportGenerator:
    """
    Report generator agent that creates formatted Markdown reports.

    Uses Claude Sonnet 4.5 to synthesize aggregated results into
    comprehensive, actionable prospecting reports.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the report generator agent.

        Args:
            settings: Configuration settings (uses defaults if not provided)
        """
        self.settings = settings or Settings()

        # Create BedrockModel for report generation
        # Good writing quality with consistent output (not using extended thinking)
        reporter_config = {
            "model_id": self.settings.reporter_model,
            "temperature": 0.4,  # Slightly creative for better prose
            "max_tokens": 8000,  # Reports can be longer
        }

        self.reporter_model = BedrockModel(**reporter_config)

        # Create the reporter agent (reused for all report generation)
        self.reporter_agent = Agent(
            model=self.reporter_model,
            system_prompt=REPORTER_SYSTEM_PROMPT,
            name="report_generator",
        )

        logger.info(
            f"Initialized ReportGenerator with model {self.settings.reporter_model}"
        )

    async def generate_report(
        self,
        results: AggregatedResults,
        original_query: Optional[str] = None
    ) -> ProspectingReport:
        """
        Generate a prospecting report from aggregated results.

        This is the main entry point for report generation. It takes
        the aggregated results and synthesizes them into a formatted
        Markdown report.

        Args:
            results: Aggregated results from the executor
            original_query: Override for original query (uses results.original_query if not provided)

        Returns:
            ProspectingReport with formatted Markdown content

        Raises:
            ValueError: If report generation fails after retries
        """
        query = original_query or results.original_query
        logger.info(f"Generating report for query: {query}")

        # Create the report generation prompt
        prompt = self._create_report_prompt(results, query)

        # Try to generate the report (with retry logic)
        max_retries = 2
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.debug(f"Report generation attempt {attempt + 1}/{max_retries}")

                # Use the reporter agent
                response = await self.reporter_agent.invoke_async(prompt)

                # Extract the Markdown content
                markdown_content = self._extract_markdown_from_response(response)

                # Create the report object
                report = ProspectingReport(
                    query_summary=self._create_query_summary(query),
                    generated_at=datetime.now(),
                    sources_used=[s.value for s in results.sources_queried],
                    markdown_content=markdown_content,
                    companies_count=len(results.companies),
                    individuals_count=len(results.individuals),
                )

                logger.info(
                    f"Report generated: {len(markdown_content)} chars, "
                    f"{report.companies_count} companies, "
                    f"{report.individuals_count} individuals"
                )
                return report

            except (ValueError, BotocoreClientError) as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

        # All retries exhausted
        logger.error(f"Failed to generate report after {max_retries} attempts: {last_error}")
        raise ValueError(f"Failed to generate report: {last_error}")

    def _create_report_prompt(self, results: AggregatedResults, query: str) -> str:
        """
        Create the prompt for report generation.

        Args:
            results: Aggregated results to report on
            query: Original user query

        Returns:
            Formatted prompt string
        """
        # Prepare structured data for the prompt
        companies_data = self._format_companies_for_prompt(results)
        individuals_data = self._format_individuals_for_prompt(results)
        news_data = self._extract_news_from_results(results)
        execution_summary = self._format_execution_summary(results)

        return f"""Generate a prospecting report for the following query and results.

ORIGINAL QUERY:
"{query}"

EXECUTION SUMMARY:
{execution_summary}

COMPANIES FOUND ({len(results.companies)}):
{companies_data}

INDIVIDUALS FOUND ({len(results.individuals)}):
{individuals_data}

RECENT NEWS & SIGNALS:
{news_data}

Please generate a comprehensive Markdown report with the following structure:

# Prospecting Report: [Create a concise title summarizing the query]

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Sources queried: {', '.join(s.value for s in results.sources_queried)}

## Executive Summary
[2-3 sentence overview of key findings]

## Companies Found
[For each relevant company, include:]
### [Company Name]
- **Overview**: [Brief description]
- **Financials**: [Revenue, employees, etc. if available]
- **Funding**: [If applicable - rounds, investors, amounts]
- **Key People**: [Directors, founders]
- **Source**: [Which data sources provided this]

## Individuals Found
[For each relevant individual, include:]
### [Name]
- **Current Role**: [Position at company]
- **Wealth Profile**: [If available from Wealth-X/Wealth Monitor]
- **Directorships**: [Other current roles]
- **Client Status**: [Prospect / Existing Client / Excluded]

## Recent News & Signals
[List relevant news items with dates and sources]

## Data Quality Notes
- [Any gaps or missing information]
- [Cross-reference discrepancies if any]
- [Data freshness notes]

## Recommended Next Steps
[Actionable suggestions based on findings]

Remember to:
- Synthesize information across sources, don't just list raw data
- Highlight the most relevant findings for the original query
- Be concise but comprehensive
- Use professional language appropriate for a private bank"""

    def _format_companies_for_prompt(self, results: AggregatedResults) -> str:
        """
        Format company data for the prompt.

        Args:
            results: Aggregated results

        Returns:
            Formatted string of company information
        """
        if not results.companies:
            return "No companies found."

        lines = []
        for company in results.companies:
            company_info = [f"- {company.name}"]

            if company.country:
                company_info.append(f"  Country: {company.country}")
            if company.city:
                company_info.append(f"  City: {company.city}")
            if company.industry:
                company_info.append(f"  Industry: {company.industry}")
            if company.status:
                company_info.append(f"  Status: {company.status}")
            if company.revenue:
                company_info.append(f"  Revenue: {company.revenue:,.0f} {company.revenue_currency}")
            if company.employee_count:
                company_info.append(f"  Employees: {company.employee_count}")
            if company.total_funding:
                company_info.append(f"  Total Funding: {company.total_funding:,.0f} {company.funding_currency}")
            if company.last_funding_round:
                company_info.append(f"  Last Round: {company.last_funding_round}")
            if company.last_funding_date:
                company_info.append(f"  Last Funding Date: {company.last_funding_date}")
            if company.last_funding_amount:
                company_info.append(f"  Last Funding Amount: {company.last_funding_amount:,.0f} {company.funding_currency}")
            if company.investors:
                company_info.append(f"  Investors: {', '.join(company.investors[:5])}")
            if company.companies_house_number:
                company_info.append(f"  Companies House #: {company.companies_house_number}")
            if company.sources:
                company_info.append(f"  Sources: {', '.join(s.value for s in company.sources)}")

            lines.append("\n".join(company_info))

        return "\n\n".join(lines)

    def _format_individuals_for_prompt(self, results: AggregatedResults) -> str:
        """
        Format individual data for the prompt.

        Args:
            results: Aggregated results

        Returns:
            Formatted string of individual information
        """
        if not results.individuals:
            return "No individuals found."

        lines = []
        for individual in results.individuals:
            ind_info = [f"- {individual.name}"]

            if individual.title:
                ind_info[0] = f"- {individual.title} {individual.name}"

            if individual.current_roles:
                for role in individual.current_roles[:3]:  # Limit to 3 roles
                    ind_info.append(f"  Current Role: {role.title} at {role.company_name}")

            if individual.nationality:
                ind_info.append(f"  Nationality: {individual.nationality}")
            if individual.country_of_residence:
                ind_info.append(f"  Residence: {individual.country_of_residence}")
            if individual.city:
                ind_info.append(f"  City: {individual.city}")

            if individual.net_worth:
                ind_info.append(f"  Net Worth: {individual.net_worth:,.0f} {individual.net_worth_currency}")
            if individual.wealth_source:
                ind_info.append(f"  Wealth Source: {individual.wealth_source}")
            if individual.liquidity:
                ind_info.append(f"  Liquidity: {individual.liquidity:,.0f} {individual.net_worth_currency}")

            if individual.interests:
                ind_info.append(f"  Interests: {', '.join(individual.interests[:5])}")
            if individual.philanthropy:
                ind_info.append(f"  Philanthropy: {', '.join(individual.philanthropy[:3])}")

            if individual.is_existing_client:
                ind_info.append("  Status: EXISTING CLIENT")
            else:
                ind_info.append("  Status: Prospect")

            if individual.sources:
                ind_info.append(f"  Sources: {', '.join(s.value for s in individual.sources)}")

            lines.append("\n".join(ind_info))

        return "\n\n".join(lines)

    def _extract_news_from_results(self, results: AggregatedResults) -> str:
        """
        Extract news items from SerpAPI results.

        Args:
            results: Aggregated results

        Returns:
            Formatted string of news items
        """
        news_items = []

        for result in results.results:
            if result.source == DataSource.SERPAPI and result.success and result.data:
                data = result.data
                if isinstance(data, dict):
                    # Check for news_results (from news search)
                    if "news_results" in data:
                        for item in data["news_results"][:5]:  # Limit to 5
                            title = item.get("title", "")
                            source = item.get("source", {}).get("name", "Unknown")
                            date = item.get("date", "")
                            snippet = item.get("snippet", "")
                            news_items.append(f"- [{date}] {title} ({source})\n  {snippet}")

                    # Check for organic_results (from web search)
                    elif "organic_results" in data:
                        for item in data["organic_results"][:3]:  # Limit to 3
                            title = item.get("title", "")
                            snippet = item.get("snippet", "")
                            news_items.append(f"- {title}\n  {snippet}")

        if not news_items:
            return "No recent news found."

        return "\n\n".join(news_items)

    def _format_execution_summary(self, results: AggregatedResults) -> str:
        """
        Format execution summary for the prompt.

        Args:
            results: Aggregated results

        Returns:
            Formatted execution summary
        """
        successful = sum(1 for r in results.results if r.success)
        failed = sum(1 for r in results.results if not r.success)

        lines = [
            f"- Total steps executed: {len(results.results)}",
            f"- Successful: {successful}",
            f"- Failed: {failed}",
            f"- Total records: {results.total_records}",
            f"- Execution time: {results.execution_time_ms}ms",
            f"- Plan confidence: {results.plan.confidence:.0%}",
        ]

        # Add step-by-step summary
        lines.append("\nStep results:")
        for result in results.results:
            status = "OK" if result.success else "FAILED"
            lines.append(
                f"  Step {result.step_id}: {result.source.value} - {status} "
                f"({result.record_count} records)"
            )
            if result.error:
                lines.append(f"    Error: {result.error}")

        return "\n".join(lines)

    def _extract_markdown_from_response(self, response: str) -> str:
        """
        Extract Markdown content from the model's response.

        Args:
            response: Raw response from the model

        Returns:
            Cleaned Markdown content
        """
        response_text = str(response).strip()

        # Remove any thinking tags if present
        if "<thinking>" in response_text:
            # Find content after </thinking>
            end_thinking = response_text.rfind("</thinking>")
            if end_thinking != -1:
                response_text = response_text[end_thinking + 11:].strip()

        # The response should be primarily Markdown
        # Clean up any potential JSON wrapper or code blocks
        if response_text.startswith("```markdown"):
            response_text = response_text[11:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        return response_text.strip()

    def _create_query_summary(self, query: str) -> str:
        """
        Create a short summary of the query for the report title.

        Args:
            query: Original query

        Returns:
            Shortened query summary (max 100 chars)
        """
        # Truncate if needed
        if len(query) <= 100:
            return query
        return query[:97] + "..."

    def to_markdown(self, report: ProspectingReport) -> str:
        """
        Get the Markdown content from a report.

        Args:
            report: The generated report

        Returns:
            Markdown string
        """
        return report.markdown_content

    def save_to_file(
        self,
        report: ProspectingReport,
        filepath: str,
        include_metadata: bool = True
    ) -> Path:
        """
        Save a report to a Markdown file.

        Args:
            report: The generated report
            filepath: Path to save the file (will add .md extension if missing)
            include_metadata: Whether to include metadata header

        Returns:
            Path to the saved file
        """
        # Ensure .md extension
        path = Path(filepath)
        if path.suffix != ".md":
            path = path.with_suffix(".md")

        # Prepare content
        content = report.markdown_content

        if include_metadata:
            metadata = [
                "---",
                f"query: {report.query_summary}",
                f"generated: {report.generated_at.isoformat()}",
                f"sources: {', '.join(report.sources_used)}",
                f"companies: {report.companies_count}",
                f"individuals: {report.individuals_count}",
                "---",
                "",
            ]
            content = "\n".join(metadata) + content

        # Write file
        path.write_text(content, encoding="utf-8")
        logger.info(f"Report saved to {path}")

        return path

    async def generate_and_save(
        self,
        results: AggregatedResults,
        filepath: str,
        original_query: Optional[str] = None,
        include_metadata: bool = True
    ) -> tuple[ProspectingReport, Path]:
        """
        Generate a report and save it to a file in one operation.

        Convenience method that combines generate_report and save_to_file.

        Args:
            results: Aggregated results from the executor
            filepath: Path to save the file
            original_query: Override for original query
            include_metadata: Whether to include metadata header

        Returns:
            Tuple of (ProspectingReport, Path to saved file)
        """
        report = await self.generate_report(results, original_query)
        saved_path = self.save_to_file(report, filepath, include_metadata)
        return report, saved_path
