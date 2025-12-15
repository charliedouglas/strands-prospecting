"""
Manual test script for the ReportGenerator agent.

Tests report generation from various AggregatedResults scenarios.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from src.agents.reporter import ReportGenerator, ProspectingReport
from src.models import (
    AggregatedResults,
    ExecutionPlan,
    PlanStep,
    SearchResult,
    DataSource,
    Company,
    Individual,
    Role,
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
        reasoning="Find UK tech companies with Series B funding, then look up directors and wealth profiles",
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
                action="get_officers",
                params={"company_number": "12345678"},
                reason="Get company directors"
            ),
            PlanStep(
                step_id=3,
                source=DataSource.WEALTHX,
                action="search_profiles",
                params={"net_worth_min": 30000000, "countries": ["GB"]},
                reason="Get wealth profiles for directors"
            ),
            PlanStep(
                step_id=4,
                source=DataSource.SERPAPI,
                action="news_search",
                params={"query": "ACME Technologies funding"},
                reason="Find recent news"
            ),
            PlanStep(
                step_id=5,
                source=DataSource.INTERNAL_CRM,
                action="check_clients",
                params={"companies": [], "individuals": []},
                reason="Check for existing clients"
            )
        ],
        clarification_needed=None,
        estimated_sources=5,
        confidence=0.85
    )


def create_comprehensive_results() -> AggregatedResults:
    """Create comprehensive test results with companies, individuals, and news."""
    plan = create_test_plan()

    # Create search results from multiple sources
    results = [
        SearchResult(
            step_id=1,
            source=DataSource.CRUNCHBASE,
            success=True,
            data={
                "count": 3,
                "entities": [
                    {
                        "uuid": "uuid-1",
                        "properties": {
                            "identifier": {"value": "ACME Technologies", "permalink": "acme-technologies"},
                            "announced_on": "2024-06-15",
                            "money_raised": {"value": 25000000, "currency": "GBP"},
                            "investment_type": "series_b",
                            "investor_identifiers": [
                                {"value": "Sequoia Capital"},
                                {"value": "Index Ventures"}
                            ]
                        }
                    },
                    {
                        "uuid": "uuid-2",
                        "properties": {
                            "identifier": {"value": "TechFlow Ltd", "permalink": "techflow"},
                            "announced_on": "2024-04-20",
                            "money_raised": {"value": 18000000, "currency": "GBP"},
                            "investment_type": "series_b"
                        }
                    }
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
                "items": [
                    {
                        "name": "SMITH, John David",
                        "officer_role": "director",
                        "appointed_on": "2018-03-15",
                        "nationality": "British"
                    },
                    {
                        "name": "DOE, Jane",
                        "officer_role": "director",
                        "appointed_on": "2019-01-10",
                        "nationality": "British"
                    }
                ]
            },
            record_count=2,
            execution_time_ms=180,
            timestamp=datetime.now()
        ),
        SearchResult(
            step_id=3,
            source=DataSource.WEALTHX,
            success=True,
            data={
                "total_count": 2,
                "profiles": [
                    {
                        "wealthx_id": "WX-123456",
                        "name": "John David Smith",
                        "net_worth": {"value": 85000000, "currency": "USD"},
                        "wealth_source": "Self-made",
                        "primary_industry": "Technology"
                    }
                ]
            },
            record_count=2,
            execution_time_ms=300,
            timestamp=datetime.now()
        ),
        SearchResult(
            step_id=4,
            source=DataSource.SERPAPI,
            success=True,
            data={
                "news_results": [
                    {
                        "title": "ACME Technologies raises £25M Series B to expand AI platform",
                        "link": "https://techcrunch.com/2024/06/15/acme-series-b",
                        "source": {"name": "TechCrunch"},
                        "date": "2 days ago",
                        "snippet": "London-based ACME Technologies has raised £25 million in Series B funding led by Sequoia Capital to expand its enterprise AI platform."
                    },
                    {
                        "title": "UK fintech sector sees record investment in H1 2024",
                        "link": "https://ft.com/content/abc123",
                        "source": {"name": "Financial Times"},
                        "date": "1 week ago",
                        "snippet": "British fintech companies attracted £4.2bn in venture capital during the first half of 2024."
                    }
                ]
            },
            record_count=2,
            execution_time_ms=150,
            timestamp=datetime.now()
        ),
        SearchResult(
            step_id=5,
            source=DataSource.INTERNAL_CRM,
            success=True,
            data={
                "matches": {
                    "companies": [
                        {"query_name": "ACME Technologies", "is_client": False, "is_prospect": True},
                        {"query_name": "TechFlow Ltd", "is_client": False, "is_prospect": False}
                    ],
                    "individuals": [
                        {"query_name": "John Smith", "is_client": False, "is_prospect": True}
                    ]
                }
            },
            record_count=3,
            execution_time_ms=50,
            timestamp=datetime.now()
        )
    ]

    # Create realistic companies
    companies = [
        Company(
            id="comp-001",
            name="ACME Technologies Ltd",
            bvd_id="GB12345678",
            companies_house_number="12345678",
            crunchbase_uuid="uuid-1",
            country="GB",
            city="London",
            region="Greater London",
            website="https://acmetech.io",
            industry="Information Technology",
            sic_codes=["62020"],
            company_type="Private Limited Company",
            status="Active",
            revenue=15000000,
            revenue_currency="GBP",
            employee_count=85,
            incorporation_date="2018-03-15",
            total_funding=42000000,
            funding_currency="USD",
            last_funding_round="Series B",
            last_funding_date="2024-06-15",
            last_funding_amount=25000000,
            investors=["Sequoia Capital", "Index Ventures", "Balderton Capital"],
            sources=[DataSource.CRUNCHBASE, DataSource.COMPANIES_HOUSE, DataSource.ORBIS]
        ),
        Company(
            id="comp-002",
            name="TechFlow Ltd",
            companies_house_number="87654321",
            country="GB",
            city="Manchester",
            industry="Information Technology",
            status="Active",
            revenue=8000000,
            revenue_currency="GBP",
            employee_count=45,
            total_funding=22000000,
            funding_currency="USD",
            last_funding_round="Series B",
            last_funding_date="2024-04-20",
            last_funding_amount=18000000,
            investors=["Accel", "LocalGlobe"],
            sources=[DataSource.CRUNCHBASE, DataSource.COMPANIES_HOUSE]
        )
    ]

    # Create individuals with wealth profiles
    individuals = [
        Individual(
            id="ind-001",
            name="John David Smith",
            wealthx_id="WX-123456",
            title="Mr",
            first_name="John",
            last_name="Smith",
            gender="Male",
            nationality="British",
            country_of_residence="United Kingdom",
            city="London",
            current_roles=[
                Role(
                    company_name="ACME Technologies Ltd",
                    company_id="comp-001",
                    title="Founder & CEO",
                    role_type="Executive",
                    start_date="2018-03-15",
                    is_current=True
                )
            ],
            net_worth=85000000,
            net_worth_currency="USD",
            wealth_source="Self-made",
            liquidity=25000000,
            interests=["Technology", "Sustainable investing", "Classical music"],
            philanthropy=["Education", "Climate change"],
            known_associates=["Jane Doe", "Michael Chen"],
            sources=[DataSource.WEALTHX, DataSource.COMPANIES_HOUSE],
            is_existing_client=False
        ),
        Individual(
            id="ind-002",
            name="Jane Doe",
            title="Dr",
            first_name="Jane",
            last_name="Doe",
            nationality="British",
            country_of_residence="United Kingdom",
            city="London",
            current_roles=[
                Role(
                    company_name="ACME Technologies Ltd",
                    company_id="comp-001",
                    title="CTO",
                    role_type="Executive",
                    start_date="2019-01-10",
                    is_current=True
                ),
                Role(
                    company_name="Tech Advisory Board",
                    title="Non-Executive Director",
                    role_type="Director",
                    is_current=True
                )
            ],
            sources=[DataSource.COMPANIES_HOUSE],
            is_existing_client=False
        )
    ]

    return AggregatedResults(
        original_query="Find UK tech companies that raised Series B in 2024 with founder wealth profiles",
        plan=plan,
        results=results,
        companies=companies,
        individuals=individuals,
        total_records=12,
        sources_queried=[
            DataSource.CRUNCHBASE,
            DataSource.COMPANIES_HOUSE,
            DataSource.WEALTHX,
            DataSource.SERPAPI,
            DataSource.INTERNAL_CRM
        ],
        execution_time_ms=930
    )


def create_minimal_results() -> AggregatedResults:
    """Create minimal test results with just a few companies."""
    plan = ExecutionPlan(
        reasoning="Simple company search",
        steps=[
            PlanStep(
                step_id=1,
                source=DataSource.COMPANIES_HOUSE,
                action="search",
                params={"query": "tech"},
                reason="Find tech companies"
            )
        ],
        clarification_needed=None,
        estimated_sources=1,
        confidence=0.7
    )

    results = [
        SearchResult(
            step_id=1,
            source=DataSource.COMPANIES_HOUSE,
            success=True,
            data={"items": [{"company_number": "12345678", "title": "TECHCO LTD"}]},
            record_count=1,
            execution_time_ms=100,
            timestamp=datetime.now()
        )
    ]

    companies = [
        Company(
            id="comp-001",
            name="TechCo Ltd",
            companies_house_number="12345678",
            country="GB",
            status="Active",
            sources=[DataSource.COMPANIES_HOUSE]
        )
    ]

    return AggregatedResults(
        original_query="Find tech companies",
        plan=plan,
        results=results,
        companies=companies,
        individuals=[],
        total_records=1,
        sources_queried=[DataSource.COMPANIES_HOUSE],
        execution_time_ms=100
    )


async def test_comprehensive_report():
    """Test report generation with comprehensive data."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Comprehensive report generation")
    logger.info("="*80)

    reporter = ReportGenerator()
    results = create_comprehensive_results()

    try:
        report = await reporter.generate_report(results)

        logger.info(f"\nReport generated successfully!")
        logger.info(f"Query summary: {report.query_summary}")
        logger.info(f"Generated at: {report.generated_at}")
        logger.info(f"Sources used: {report.sources_used}")
        logger.info(f"Companies count: {report.companies_count}")
        logger.info(f"Individuals count: {report.individuals_count}")
        logger.info(f"Content length: {len(report.markdown_content)} chars")

        # Print the full report
        logger.info("\n" + "-"*80)
        logger.info("GENERATED REPORT:")
        logger.info("-"*80)
        print(report.markdown_content)
        logger.info("-"*80)

        # Verify report structure
        assert len(report.markdown_content) > 500, "Report should have substantial content"
        assert "ACME" in report.markdown_content, "Report should mention ACME Technologies"
        assert "Series B" in report.markdown_content, "Report should mention funding round"

        logger.info("\n✓ Test passed!")
        return report

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        raise


async def test_minimal_report():
    """Test report generation with minimal data."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Minimal report generation")
    logger.info("="*80)

    reporter = ReportGenerator()
    results = create_minimal_results()

    try:
        report = await reporter.generate_report(results)

        logger.info(f"\nReport generated successfully!")
        logger.info(f"Content length: {len(report.markdown_content)} chars")

        # Print abbreviated report
        logger.info("\n" + "-"*80)
        logger.info("GENERATED REPORT (first 1000 chars):")
        logger.info("-"*80)
        print(report.markdown_content[:1000])
        if len(report.markdown_content) > 1000:
            print("...")
        logger.info("-"*80)

        assert len(report.markdown_content) > 100, "Report should have some content"

        logger.info("\n✓ Test passed!")
        return report

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        raise


async def test_save_to_file():
    """Test saving report to file."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Save report to file")
    logger.info("="*80)

    reporter = ReportGenerator()
    results = create_comprehensive_results()

    try:
        # Generate report
        report = await reporter.generate_report(results)

        # Save to file
        output_path = Path("test_output_report.md")
        saved_path = reporter.save_to_file(report, str(output_path), include_metadata=True)

        logger.info(f"\nReport saved to: {saved_path}")
        assert saved_path.exists(), "File should exist"

        # Read back and verify
        content = saved_path.read_text()
        assert "---" in content, "Should have YAML frontmatter"
        assert "query:" in content, "Should have query in metadata"

        logger.info(f"File size: {len(content)} bytes")

        # Clean up
        saved_path.unlink()
        logger.info("Test file cleaned up")

        logger.info("\n✓ Test passed!")

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        raise


async def test_generate_and_save():
    """Test combined generate and save operation."""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Generate and save in one operation")
    logger.info("="*80)

    reporter = ReportGenerator()
    results = create_comprehensive_results()

    try:
        report, saved_path = await reporter.generate_and_save(
            results,
            "test_combined_report.md",
            include_metadata=True
        )

        logger.info(f"\nReport generated and saved!")
        logger.info(f"Path: {saved_path}")
        logger.info(f"Companies: {report.companies_count}")
        logger.info(f"Individuals: {report.individuals_count}")

        assert saved_path.exists(), "File should exist"

        # Clean up
        saved_path.unlink()
        logger.info("Test file cleaned up")

        logger.info("\n✓ Test passed!")

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        raise


async def test_markdown_export():
    """Test Markdown export utility."""
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Markdown export utility")
    logger.info("="*80)

    reporter = ReportGenerator()
    results = create_minimal_results()

    try:
        report = await reporter.generate_report(results)
        markdown = reporter.to_markdown(report)

        assert markdown == report.markdown_content, "to_markdown should return content"
        logger.info(f"Markdown length: {len(markdown)} chars")

        logger.info("\n✓ Test passed!")

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        raise


async def main():
    """Run all tests."""
    logger.info("Starting ReportGenerator tests...")
    logger.info("Note: These tests call real AWS Bedrock API\n")

    try:
        # Run comprehensive test first (most important)
        await test_comprehensive_report()

        # Run other tests
        await test_minimal_report()
        await test_save_to_file()
        await test_generate_and_save()
        await test_markdown_export()

        logger.info("\n" + "="*80)
        logger.info("All tests passed!")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"\nTests failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
