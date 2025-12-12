"""
End-to-end test of the complete prospecting workflow.

Tests: Query -> Plan -> Approval -> Execute -> Results
"""

import asyncio
import logging
from dotenv import load_dotenv

from src.config import Settings
from src.orchestrator import ProspectingOrchestrator
from src.models import UserFeedback, ApprovalStatus

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoApprovalHandler:
    """Test approval handler that auto-approves plans."""

    async def request_approval(self, summary: str, revision_number: int) -> UserFeedback:
        """Auto-approve all plans."""
        logger.info(f"AUTO-APPROVING plan revision {revision_number}")
        logger.info(f"Plan summary:\n{summary}")
        return UserFeedback(
            status=ApprovalStatus.APPROVED,
            feedback_text="Auto-approved for testing"
        )


async def test_end_to_end():
    """Test the complete workflow."""
    # Load environment
    load_dotenv()
    settings = Settings()

    # Create orchestrator with auto-approval
    orchestrator = ProspectingOrchestrator(
        settings=settings,
        approval_handler=AutoApprovalHandler()
    )

    # Test query
    query = "Find UK tech companies that raised Series B funding in 2024"

    logger.info("=" * 80)
    logger.info("STARTING END-TO-END TEST")
    logger.info("=" * 80)
    logger.info(f"Query: {query}")
    logger.info("")

    # Run workflow
    result = await orchestrator.run(query)

    # Display results
    logger.info("=" * 80)
    logger.info("WORKFLOW RESULTS")
    logger.info("=" * 80)
    logger.info(f"Status: {result['status']}")

    if result['status'] == 'executed':
        summary = result['summary']
        logger.info(f"\nExecution Summary:")
        logger.info(f"  Steps Executed: {summary['steps_executed']}")
        logger.info(f"  Steps Succeeded: {summary['steps_succeeded']}")
        logger.info(f"  Steps Failed: {summary['steps_failed']}")
        logger.info(f"  Total Records: {summary['total_records']}")
        logger.info(f"  Execution Time: {summary['execution_time_ms']}ms")
        logger.info(f"  Sources: {summary['sources_queried']}")

        logger.info(f"\nStep Results:")
        for i, step_result in enumerate(result['execution_results']['results'], 1):
            status = "✓" if step_result['success'] else "✗"
            logger.info(
                f"  {status} Step {i}: {step_result['source']} - "
                f"{step_result['record_count']} records in {step_result['execution_time_ms']}ms"
            )
            if step_result.get('error'):
                logger.info(f"     Error: {step_result['error']}")

        logger.info("")
        logger.info("✅ END-TO-END TEST PASSED!")
    else:
        logger.error(f"❌ Unexpected status: {result['status']}")
        logger.error(f"Result: {result}")

    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_end_to_end())
