"""Session management for the prospecting agent.

Maintains conversation state, tracks search history, and manages the full workflow
for prospecting queries including clarifications and revisions.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

from src.config import Settings
from src.orchestrator import ProspectingOrchestrator
from src.approval_handler import ApprovalHandler
from src.models import (
    SufficiencyStatus,
    ApprovalStatus,
    WorkflowRejectedError,
)

logger = logging.getLogger(__name__)


@dataclass
class QueryHistory:
    """Tracks a single query and its results through the workflow."""

    query: str
    timestamp: datetime
    plan: Optional[Dict[str, Any]] = None
    execution_results: Optional[Dict[str, Any]] = None
    sufficiency_result: Optional[Dict[str, Any]] = None
    report: Optional[str] = None
    clarifications: List[Dict[str, str]] = field(default_factory=list)
    status: str = "pending"  # pending, planning, planned, executing, executed, checking, sufficient, insufficient


@dataclass
class SessionStats:
    """Statistics about the current session."""

    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    clarifications_requested: int = 0
    total_execution_time_ms: int = 0
    total_records_found: int = 0
    unique_companies: int = 0
    unique_individuals: int = 0


class ProspectingSession:
    """
    Manages a conversation session for prospecting queries.

    This class maintains state across multiple queries in a single session,
    allowing users to:
    - Ask follow-up questions
    - Request clarifications
    - Review previous results
    - Export session data
    """

    def __init__(self, settings: Settings, approval_handler: ApprovalHandler):
        """Initialize a new prospecting session.

        Args:
            settings: Application settings
            approval_handler: Handler for user approval decisions
        """
        self.settings = settings
        self.approval_handler = approval_handler
        self.orchestrator = ProspectingOrchestrator(settings, approval_handler)

        # Session state
        self.session_id = datetime.now().isoformat()
        self.query_history: List[QueryHistory] = []
        self.stats = SessionStats()
        self.current_results: Optional[Dict[str, Any]] = None

        logger.info(f"Prospecting session {self.session_id} initialized")

    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """
        Process a user query through the full prospecting workflow.

        Handles:
        - Planning (with clarification if needed)
        - User approval
        - Execution
        - Sufficiency checking (with retry if needed)
        - Report generation

        Args:
            user_query: The user's prospecting query

        Returns:
            Dictionary with workflow results and status

        Raises:
            WorkflowRejectedError: If user rejects the plan
            Exception: For unexpected errors
        """
        # Create query history entry
        query_entry = QueryHistory(query=user_query, timestamp=datetime.now())
        self.query_history.append(query_entry)
        self.stats.total_queries += 1

        try:
            logger.info(f"Processing query: {user_query}")

            # Run the full orchestrator workflow
            result = await self.orchestrator.run(user_query)

            # Update query entry with results
            query_entry.status = result.get("status", "unknown")
            query_entry.plan = result.get("plan")
            query_entry.execution_results = result.get("execution_results")
            query_entry.sufficiency_result = result.get("sufficiency")

            # Store current results for follow-up queries
            self.current_results = result

            # Update session statistics
            self._update_stats(result)

            # Log success or issues
            if result.get("status") == "sufficient":
                self.stats.successful_queries += 1
                logger.info(f"Query succeeded with sufficient data")
            elif result.get("status") in ["clarification_needed", "insufficient"]:
                logger.info(f"Query needs further action: {result.get('status')}")
            else:
                self.stats.failed_queries += 1
                logger.warning(f"Query incomplete: {result.get('status')}")

            return result

        except WorkflowRejectedError:
            query_entry.status = "rejected"
            self.stats.failed_queries += 1
            logger.warning("User rejected the workflow")
            raise

        except Exception as e:
            query_entry.status = "error"
            self.stats.failed_queries += 1
            logger.error(f"Error processing query: {e}", exc_info=True)
            raise

    async def clarify_and_retry(self, clarification_response: str) -> Dict[str, Any]:
        """
        Process a clarification response and retry the workflow.

        This is called when the planner or sufficiency checker needs
        clarification from the user.

        Args:
            clarification_response: User's response to the clarification question

        Returns:
            Updated workflow results
        """
        if not self.query_history:
            raise ValueError("No query in progress to clarify")

        current_query = self.query_history[-1]
        current_query.clarifications.append({
            "timestamp": datetime.now().isoformat(),
            "response": clarification_response
        })

        logger.info(f"Retrying query with clarification: {clarification_response}")

        # For now, retry with the original query plus clarification
        # In a more sophisticated system, this could feed into the planner
        enhanced_query = f"{current_query.query}\n\nClarification: {clarification_response}"

        try:
            result = await self.orchestrator.run(enhanced_query)
            current_query.status = result.get("status", "unknown")
            self.current_results = result
            self._update_stats(result)

            if result.get("status") == "sufficient":
                self.stats.successful_queries += 1

            return result

        except Exception as e:
            logger.error(f"Error during clarification retry: {e}", exc_info=True)
            raise

    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session."""
        return {
            "session_id": self.session_id,
            "total_queries": self.stats.total_queries,
            "successful_queries": self.stats.successful_queries,
            "failed_queries": self.stats.failed_queries,
            "clarifications_requested": self.stats.clarifications_requested,
            "total_execution_time_ms": self.stats.total_execution_time_ms,
            "total_records_found": self.stats.total_records_found,
            "unique_companies": self.stats.unique_companies,
            "unique_individuals": self.stats.unique_individuals,
            "query_count": len(self.query_history),
        }

    def get_query_history(self) -> List[Dict[str, Any]]:
        """Get the history of all queries in this session."""
        return [
            {
                "query": q.query,
                "timestamp": q.timestamp.isoformat(),
                "status": q.status,
                "clarifications_count": len(q.clarifications),
            }
            for q in self.query_history
        ]

    def _update_stats(self, result: Dict[str, Any]) -> None:
        """Update session statistics based on workflow result."""
        # Execution stats
        if result.get("execution_results"):
            summary = result["execution_results"].get("summary", {})
            self.stats.total_execution_time_ms += summary.get("execution_time_ms", 0)
            self.stats.total_records_found += summary.get("total_records", 0)
            self.stats.unique_companies += summary.get("companies_found", 0)
            self.stats.unique_individuals += summary.get("individuals_found", 0)

        # Clarification stats
        if result.get("status") == "clarification_needed":
            self.stats.clarifications_requested += 1


class CLIFormatter:
    """Formats output for the CLI with colors and progress indicators."""

    # ANSI color codes
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RED = "\033[91m"
    CYAN = "\033[96m"

    @staticmethod
    def header(text: str, width: int = 70) -> str:
        """Format a header section."""
        return f"\n{CLIFormatter.BOLD}{CLIFormatter.CYAN}{'=' * width}{CLIFormatter.RESET}\n{CLIFormatter.BOLD}{text}{CLIFormatter.RESET}\n{CLIFormatter.BOLD}{CLIFormatter.CYAN}{'=' * width}{CLIFormatter.RESET}\n"

    @staticmethod
    def section(text: str) -> str:
        """Format a section title."""
        return f"\n{CLIFormatter.BOLD}{CLIFormatter.BLUE}► {text}{CLIFormatter.RESET}"

    @staticmethod
    def success(text: str) -> str:
        """Format a success message."""
        return f"{CLIFormatter.GREEN}✓ {text}{CLIFormatter.RESET}"

    @staticmethod
    def warning(text: str) -> str:
        """Format a warning message."""
        return f"{CLIFormatter.YELLOW}⚠ {text}{CLIFormatter.RESET}"

    @staticmethod
    def error(text: str) -> str:
        """Format an error message."""
        return f"{CLIFormatter.RED}✗ {text}{CLIFormatter.RESET}"

    @staticmethod
    def info(text: str) -> str:
        """Format an info message."""
        return f"{CLIFormatter.CYAN}ℹ {text}{CLIFormatter.RESET}"

    @staticmethod
    def progress(text: str, current: int, total: int) -> str:
        """Format a progress message."""
        return f"{CLIFormatter.DIM}[{current}/{total}] {text}...{CLIFormatter.RESET}"

    @staticmethod
    def dim(text: str) -> str:
        """Format dimmed text."""
        return f"{CLIFormatter.DIM}{text}{CLIFormatter.RESET}"

    @staticmethod
    def format_result(result: Dict[str, Any]) -> str:
        """Format a complete workflow result for display."""
        output = []
        status = result.get("status", "unknown")

        if status == "sufficient":
            output.append(CLIFormatter.header("PROSPECTING RESULTS"))
            output.append(CLIFormatter.success("Sufficient data collected"))

            # Execution summary
            if result.get("summary"):
                summary = result["summary"]
                output.append(CLIFormatter.section("Execution Summary"))
                output.append(f"  Steps executed: {summary.get('steps_executed', 0)}")
                output.append(f"  {CLIFormatter.success(str(summary.get('steps_succeeded', 0)) + ' succeeded')}")
                if summary.get("steps_failed", 0) > 0:
                    output.append(f"  {CLIFormatter.warning(str(summary.get('steps_failed', 0)) + ' failed')}")
                output.append(f"  Records found: {summary.get('total_records', 0)}")
                output.append(f"  Companies: {summary.get('companies_found', 0)}")
                output.append(f"  Individuals: {summary.get('individuals_found', 0)}")
                output.append(f"  Execution time: {summary.get('execution_time_ms', 0)}ms")
                output.append(f"  Sources: {', '.join(summary.get('sources_queried', []))}")

            # Report
            if result.get("report"):
                output.append("\n" + CLIFormatter.section("Report"))
                output.append(result["report"].get("markdown_content", ""))

        elif status == "insufficient":
            output.append(CLIFormatter.header("INSUFFICIENT DATA"))
            output.append(CLIFormatter.warning("Could not collect sufficient data to answer your query"))
            output.append(f"\nReason: {result.get('reasoning', 'Unknown')}")
            if result.get("gaps"):
                output.append("\nIdentified gaps:")
                for gap in result["gaps"]:
                    output.append(f"  • {gap}")
            output.append(f"\n{result.get('message', '')}")

        elif status == "clarification_needed":
            output.append(CLIFormatter.header("CLARIFICATION NEEDED"))
            clarification = result.get("clarification", {})
            output.append(f"\n{clarification.get('question', 'Please provide more information')}")
            output.append(f"{CLIFormatter.dim(clarification.get('context', ''))}")

            if clarification.get("options"):
                output.append("\nOptions:")
                for i, option in enumerate(clarification["options"], 1):
                    output.append(f"  {i}. {option}")

        return "\n".join(output)
