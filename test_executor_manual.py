"""
Manual test for the ExecutorAgent.

This test creates a simple ExecutionPlan with dependencies and
verifies that the executor handles them correctly.
"""

import asyncio
import logging
from src.models import ExecutionPlan, PlanStep, DataSource
from src.agents.executor import ExecutorAgent

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_executor():
    """Test the executor with a simple plan."""

    # Create a test plan with dependencies
    plan = ExecutionPlan(
        reasoning="Test dependency resolution with Companies House",
        steps=[
            PlanStep(
                step_id=1,
                source=DataSource.COMPANIES_HOUSE,
                action="search",
                params={"query": "ACME Technologies", "limit": 5},
                reason="Find company by name",
                depends_on=[]
            ),
            PlanStep(
                step_id=2,
                source=DataSource.COMPANIES_HOUSE,
                action="get_company",
                params={"company_number": "$step_1.items[0].company_number"},
                reason="Get full company details using number from step 1",
                depends_on=[1]
            ),
            PlanStep(
                step_id=3,
                source=DataSource.COMPANIES_HOUSE,
                action="get_officers",
                params={"company_number": "$step_1.items[0].company_number"},
                reason="Get company officers using number from step 1",
                depends_on=[1]
            ),
        ],
        clarification_needed=None,
        estimated_sources=1,
        confidence=0.9
    )

    logger.info("=" * 80)
    logger.info("TEST: Executing plan with dependencies")
    logger.info("=" * 80)

    # Create executor and run the plan
    executor = ExecutorAgent()
    results = await executor.execute_plan(plan, "test query")

    # Print results
    logger.info("=" * 80)
    logger.info("RESULTS:")
    logger.info("=" * 80)
    logger.info(f"Total steps executed: {len(results.results)}")
    logger.info(f"Total records: {results.total_records}")
    logger.info(f"Total execution time: {results.execution_time_ms}ms")
    logger.info(f"Sources queried: {[s.value for s in results.sources_queried]}")
    logger.info("")

    # Print each step result
    for i, result in enumerate(results.results, 1):
        status = "✓ SUCCESS" if result.success else "✗ FAILED"
        logger.info(f"Step {result.step_id}: {result.source.value}.{plan.steps[i-1].action}")
        logger.info(f"  Status: {status}")
        logger.info(f"  Records: {result.record_count}")
        logger.info(f"  Time: {result.execution_time_ms}ms")
        if result.error:
            logger.info(f"  Error: {result.error}")
        else:
            # Print a sample of the data
            if isinstance(result.data, dict):
                if "items" in result.data:
                    logger.info(f"  Data: {len(result.data['items'])} items")
                    if result.data['items']:
                        logger.info(f"  First item keys: {list(result.data['items'][0].keys())}")
                elif "company_number" in result.data:
                    logger.info(f"  Company: {result.data.get('company_name', 'N/A')}")
                    logger.info(f"  Number: {result.data.get('company_number', 'N/A')}")
                else:
                    logger.info(f"  Data keys: {list(result.data.keys())[:5]}")
        logger.info("")

    # Verify dependencies worked
    logger.info("=" * 80)
    logger.info("VERIFICATION:")
    logger.info("=" * 80)

    # Check all steps succeeded
    all_success = all(r.success for r in results.results)
    logger.info(f"✓ All steps succeeded: {all_success}")

    # Check step 2 and 3 used data from step 1
    if len(results.results) >= 3:
        step1_data = results.results[0].data
        step2_data = results.results[1].data
        step3_data = results.results[2].data

        if step1_data and "items" in step1_data and len(step1_data["items"]) > 0:
            expected_company_number = step1_data["items"][0]["company_number"]
            step2_company_number = step2_data.get("company_number") if step2_data else None

            if step2_company_number == expected_company_number:
                logger.info(f"✓ Step 2 used company_number from step 1: {expected_company_number}")
            else:
                logger.warning(f"✗ Step 2 company_number mismatch: expected {expected_company_number}, got {step2_company_number}")

            # Check step 3 got officers for the same company
            if step3_data and "items" in step3_data:
                logger.info(f"✓ Step 3 retrieved {len(step3_data['items'])} officers")
            else:
                logger.warning("✗ Step 3 did not retrieve officers")

    logger.info("=" * 80)
    logger.info("TEST COMPLETE")
    logger.info("=" * 80)

    return results


if __name__ == "__main__":
    asyncio.run(test_executor())
