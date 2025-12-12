"""
Manual test script for the SufficiencyChecker agent.

Tests various scenarios to ensure the checker evaluates results correctly.
"""

import asyncio
import logging
from datetime import datetime

from src.agents import SufficiencyChecker, SufficiencyStatus
from src.models import (
    AggregatedResults,
    ExecutionPlan,
    PlanStep,
    SearchResult,
    DataSource,
    Company,
    Individual,
)
from src.config import Settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_plan() -> ExecutionPlan:
    """Create a test execution plan."""
    return ExecutionPlan(
        reasoning="Test plan for finding UK tech companies with Series B funding",
        steps=[
            PlanStep(
                step_id=1,
                source=DataSource.CRUNCHBASE,
                action="search_funding",
                params={"investment_type": "series_b", "location": "united-kingdom"},
                reason="Find UK Series B rounds"
            ),
            PlanStep(
                step_id=2,
                source=DataSource.COMPANIES_HOUSE,
                action="search",
                params={"query": "tech"},
                reason="Get company details"
            ),
            PlanStep(
                step_id=3,
                source=DataSource.INTERNAL_CRM,
                action="check_clients",
                params={"companies": []},
                reason="Check for existing clients"
            )
        ],
        clarification_needed=None,
        estimated_sources=3,
        confidence=0.85
    )


def create_sufficient_results() -> AggregatedResults:
    """Create test results that should be marked as SUFFICIENT."""
    plan = create_test_plan()

    # All steps succeeded with good data - more realistic for prospecting
    results = [
        SearchResult(
            step_id=1,
            source=DataSource.CRUNCHBASE,
            success=True,
            data={
                "count": 12,
                "entities": [
                    {"uuid": f"uuid-{i}", "properties": {"identifier": {"value": f"Company {i}"}}}
                    for i in range(1, 13)
                ]
            },
            record_count=12,
            execution_time_ms=250,
            timestamp=datetime.now()
        ),
        SearchResult(
            step_id=2,
            source=DataSource.COMPANIES_HOUSE,
            success=True,
            data={
                "total_results": 12,
                "items": [
                    {"company_number": f"1234567{i}", "title": f"COMPANY {i} LTD"}
                    for i in range(1, 13)
                ]
            },
            record_count=12,
            execution_time_ms=180,
            timestamp=datetime.now()
        ),
        SearchResult(
            step_id=3,
            source=DataSource.INTERNAL_CRM,
            success=True,
            data={
                "matches": {
                    "companies": [
                        {
                            "query_name": f"Company {i}",
                            "is_client": False,
                            "is_prospect": True
                        }
                        for i in range(1, 13)
                    ]
                }
            },
            record_count=12,
            execution_time_ms=50,
            timestamp=datetime.now()
        )
    ]

    # Add realistic mock companies with more details
    companies = [
        Company(
            id=str(i),
            name=f"Company {i} Ltd",
            country="GB",
            industry="Technology",
            revenue=15000000.0 + (i * 1000000),
            employee_count=50 + (i * 10),
            total_funding=25000000.0,
            last_funding_round="Series B",
            sources=[DataSource.CRUNCHBASE, DataSource.COMPANIES_HOUSE]
        )
        for i in range(1, 13)
    ]

    # Add some individuals (founders/directors) for prospecting
    individuals = [
        Individual(
            id=f"ind-{i}",
            name=f"John Smith {i}",
            first_name="John",
            last_name=f"Smith{i}",
            current_roles=[],
            sources=[DataSource.COMPANIES_HOUSE]
        )
        for i in range(1, 9)
    ]

    return AggregatedResults(
        original_query="Find UK tech companies that raised Series B in 2024",
        plan=plan,
        results=results,
        companies=companies,
        individuals=individuals,
        total_records=32,
        sources_queried=[DataSource.CRUNCHBASE, DataSource.COMPANIES_HOUSE, DataSource.INTERNAL_CRM],
        execution_time_ms=480
    )


def create_missing_data_results() -> AggregatedResults:
    """Create test results with critical gaps that need RETRY."""
    plan = create_test_plan()

    # Step 1 succeeded but step 2 failed
    results = [
        SearchResult(
            step_id=1,
            source=DataSource.CRUNCHBASE,
            success=True,
            data={"count": 5, "entities": []},
            record_count=5,
            execution_time_ms=250,
            timestamp=datetime.now()
        ),
        SearchResult(
            step_id=2,
            source=DataSource.COMPANIES_HOUSE,
            success=False,
            data=None,
            error="Connection timeout",
            record_count=0,
            execution_time_ms=30000,
            timestamp=datetime.now()
        ),
        SearchResult(
            step_id=3,
            source=DataSource.INTERNAL_CRM,
            success=True,
            data={"matches": {"companies": []}},
            record_count=0,
            execution_time_ms=50,
            timestamp=datetime.now()
        )
    ]

    return AggregatedResults(
        original_query="Find UK tech companies that raised Series B with founder details",
        plan=plan,
        results=results,
        companies=[],  # No companies because step 2 failed
        individuals=[],  # Asked for founders but no data
        total_records=5,
        sources_queried=[DataSource.CRUNCHBASE, DataSource.COMPANIES_HOUSE, DataSource.INTERNAL_CRM],
        execution_time_ms=30300
    )


def create_all_clients_results() -> AggregatedResults:
    """Create test results where all matches are existing clients."""
    plan = create_test_plan()

    results = [
        SearchResult(
            step_id=1,
            source=DataSource.CRUNCHBASE,
            success=True,
            data={
                "count": 3,
                "entities": [
                    {"uuid": "1", "properties": {"identifier": {"value": "Client Corp"}}},
                ]
            },
            record_count=3,
            execution_time_ms=250,
            timestamp=datetime.now()
        ),
        SearchResult(
            step_id=2,
            source=DataSource.COMPANIES_HOUSE,
            success=True,
            data={
                "total_results": 3,
                "items": [
                    {"company_number": "11111111", "title": "CLIENT CORP LTD"},
                ]
            },
            record_count=3,
            execution_time_ms=180,
            timestamp=datetime.now()
        ),
        SearchResult(
            step_id=3,
            source=DataSource.INTERNAL_CRM,
            success=True,
            data={
                "matches": {
                    "companies": [
                        {
                            "query_name": "Client Corp",
                            "is_client": True,
                            "is_prospect": False,
                            "client_id": "CL-001"
                        },
                        {
                            "query_name": "Another Client",
                            "is_client": True,
                            "is_prospect": False,
                            "client_id": "CL-002"
                        }
                    ]
                }
            },
            record_count=2,
            execution_time_ms=50,
            timestamp=datetime.now()
        )
    ]

    # All companies are clients
    companies = [
        Company(
            id="1",
            name="Client Corp",
            country="GB",
            industry="Technology",
            sources=[DataSource.CRUNCHBASE, DataSource.COMPANIES_HOUSE]
        )
    ]

    return AggregatedResults(
        original_query="Find UK tech companies with Series B funding",
        plan=plan,
        results=results,
        companies=companies,
        individuals=[],
        total_records=8,
        sources_queried=[DataSource.CRUNCHBASE, DataSource.COMPANIES_HOUSE, DataSource.INTERNAL_CRM],
        execution_time_ms=480
    )


def create_empty_results() -> AggregatedResults:
    """Create test results where queries succeeded but found nothing."""
    plan = create_test_plan()

    results = [
        SearchResult(
            step_id=1,
            source=DataSource.CRUNCHBASE,
            success=True,
            data={"count": 0, "entities": []},
            record_count=0,
            execution_time_ms=250,
            timestamp=datetime.now()
        ),
        SearchResult(
            step_id=2,
            source=DataSource.COMPANIES_HOUSE,
            success=True,
            data={"total_results": 0, "items": []},
            record_count=0,
            execution_time_ms=180,
            timestamp=datetime.now()
        ),
        SearchResult(
            step_id=3,
            source=DataSource.INTERNAL_CRM,
            success=True,
            data={"matches": {"companies": []}},
            record_count=0,
            execution_time_ms=50,
            timestamp=datetime.now()
        )
    ]

    return AggregatedResults(
        original_query="Find UK biotech companies founded in 1800",  # Clearly wrong criteria
        plan=plan,
        results=results,
        companies=[],
        individuals=[],
        total_records=0,
        sources_queried=[DataSource.CRUNCHBASE, DataSource.COMPANIES_HOUSE, DataSource.INTERNAL_CRM],
        execution_time_ms=480
    )


async def test_sufficient():
    """Test scenario where results are sufficient."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: SUFFICIENT results")
    logger.info("="*80)

    checker = SufficiencyChecker()
    results = create_sufficient_results()

    try:
        sufficiency = await checker.evaluate(results)

        logger.info(f"\nStatus: {sufficiency.status.value}")
        logger.info(f"Reasoning: {sufficiency.reasoning}")
        logger.info(f"Gaps: {sufficiency.gaps}")
        logger.info(f"Clarification needed: {sufficiency.clarification}")
        logger.info(f"Retry steps: {sufficiency.retry_steps}")

        assert sufficiency.status == SufficiencyStatus.SUFFICIENT, \
            f"Expected SUFFICIENT, got {sufficiency.status}"
        assert len(sufficiency.gaps) == 0, "Should have no gaps"
        assert sufficiency.clarification is None, "Should not need clarification"

        logger.info("✓ Test passed!")

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        raise


async def test_missing_data():
    """Test scenario where critical data is missing."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: RETRY_NEEDED (missing data)")
    logger.info("="*80)

    checker = SufficiencyChecker()
    results = create_missing_data_results()

    try:
        sufficiency = await checker.evaluate(results)

        logger.info(f"\nStatus: {sufficiency.status.value}")
        logger.info(f"Reasoning: {sufficiency.reasoning}")
        logger.info(f"Gaps: {sufficiency.gaps}")
        logger.info(f"Retry steps: {sufficiency.retry_steps}")

        assert sufficiency.status == SufficiencyStatus.RETRY_NEEDED, \
            f"Expected RETRY_NEEDED, got {sufficiency.status}"
        assert len(sufficiency.gaps) > 0, "Should identify gaps"
        assert 2 in sufficiency.retry_steps, "Should suggest retrying step 2"

        logger.info("✓ Test passed!")

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        raise


async def test_all_clients():
    """Test scenario where all results are existing clients."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: CLARIFICATION_NEEDED (all clients)")
    logger.info("="*80)

    checker = SufficiencyChecker()
    results = create_all_clients_results()

    try:
        sufficiency = await checker.evaluate(results)

        logger.info(f"\nStatus: {sufficiency.status.value}")
        logger.info(f"Reasoning: {sufficiency.reasoning}")
        logger.info(f"Gaps: {sufficiency.gaps}")
        logger.info(f"Clarification: {sufficiency.clarification}")

        assert sufficiency.status == SufficiencyStatus.CLARIFICATION_NEEDED, \
            f"Expected CLARIFICATION_NEEDED, got {sufficiency.status}"
        assert sufficiency.clarification is not None, "Should request clarification"

        logger.info("✓ Test passed!")

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        raise


async def test_empty_results():
    """Test scenario where queries return no results."""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: CLARIFICATION_NEEDED (empty results)")
    logger.info("="*80)

    checker = SufficiencyChecker()
    results = create_empty_results()

    try:
        sufficiency = await checker.evaluate(results)

        logger.info(f"\nStatus: {sufficiency.status.value}")
        logger.info(f"Reasoning: {sufficiency.reasoning}")
        logger.info(f"Gaps: {sufficiency.gaps}")
        logger.info(f"Clarification: {sufficiency.clarification}")

        # Empty results could be CLARIFICATION_NEEDED or RETRY_NEEDED
        assert sufficiency.status in [SufficiencyStatus.CLARIFICATION_NEEDED, SufficiencyStatus.RETRY_NEEDED], \
            f"Expected CLARIFICATION_NEEDED or RETRY_NEEDED, got {sufficiency.status}"

        logger.info("✓ Test passed!")

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        raise


async def test_client_filtering():
    """Test client filtering functionality."""
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Client filtering")
    logger.info("="*80)

    checker = SufficiencyChecker()
    results = create_all_clients_results()

    try:
        filtered = checker.filter_existing_clients(results)

        logger.info(f"\nOriginal companies: {len(results.companies)}")
        logger.info(f"Filtered companies: {len(filtered.companies)}")

        # Should filter out existing clients
        assert len(filtered.companies) < len(results.companies), \
            "Should have filtered out client companies"

        logger.info("✓ Test passed!")

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        raise


async def main():
    """Run all tests."""
    logger.info("Starting SufficiencyChecker tests...")
    logger.info("Note: These tests call real AWS Bedrock API\n")

    try:
        await test_sufficient()
        await test_missing_data()
        await test_all_clients()
        await test_empty_results()
        await test_client_filtering()

        logger.info("\n" + "="*80)
        logger.info("All tests passed! ✓")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"\nTests failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
