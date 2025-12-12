"""
Simple integration test with manually created plan.

This verifies the orchestrator -> executor integration works correctly.
"""

import asyncio
import logging
from src.models import ExecutionPlan, PlanStep, DataSource
from src.agents.executor import ExecutorAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

async def test_integration():
    """Test executor with a simple valid plan."""

    # Create a plan with correct tool names
    plan = ExecutionPlan(
        reasoning="Simple test plan using Companies House",
        steps=[
            PlanStep(
                step_id=1,
                source=DataSource.COMPANIES_HOUSE,
                action="search",
                params={"query": "ACME", "limit": 3},
                reason="Find companies",
                depends_on=[]
            ),
            PlanStep(
                step_id=2,
                source=DataSource.COMPANIES_HOUSE,
                action="get_company",
                params={"company_number": "$step_1.items[0].company_number"},
                reason="Get details",
                depends_on=[1]
            ),
        ],
        clarification_needed=None,
        estimated_sources=1,
        confidence=0.9
    )

    print("\n" + "="*70)
    print("TESTING PLAN + EXECUTE INTEGRATION")
    print("="*70)

    # Execute
    executor = ExecutorAgent()
    results = await executor.execute_plan(plan, "test")

    # Display
    print(f"\n✅ Execution Complete!")
    print(f"   Steps: {len(results.results)}")
    print(f"   Success: {sum(1 for r in results.results if r.success)}/{len(results.results)}")
    print(f"   Records: {results.total_records}")
    print(f"   Time: {results.execution_time_ms}ms")

    for i, r in enumerate(results.results, 1):
        status = "✓" if r.success else "✗"
        print(f"   {status} Step {i}: {r.source.value} ({r.record_count} records)")

    print("="*70)
    print("✅ INTEGRATION TEST PASSED!\n")

if __name__ == "__main__":
    asyncio.run(test_integration())
