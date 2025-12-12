"""
Test suite for data models.

Tests Pydantic model creation, validation, and JSON serialization/deserialization
for all models in the prospecting agent.
"""

import json
from datetime import datetime
import pytest

from src.models import (
    # Planning
    DataSource,
    PlanStep,
    ClarificationRequest,
    ExecutionPlan,
    # Results
    SearchResult,
    AggregatedResults,
    # Prospects
    Role,
    Company,
    Individual,
)


class TestPlanningModels:
    """Tests for planning-related models."""

    def test_data_source_enum(self):
        """Test DataSource enum values."""
        assert DataSource.ORBIS.value == "orbis"
        assert DataSource.WEALTHX.value == "wealthx"
        assert DataSource.CRUNCHBASE.value == "crunchbase"
        assert DataSource.INTERNAL_CRM.value == "internal_crm"

        # Test all 9 sources are present
        assert len(DataSource) == 9

    def test_plan_step_creation(self):
        """Test creating a PlanStep instance."""
        step = PlanStep(
            step_id=1,
            source=DataSource.CRUNCHBASE,
            action="search_funding",
            params={"investment_type": "series_b", "location": "united-kingdom"},
            reason="Find UK Series B rounds",
            depends_on=[]
        )

        assert step.step_id == 1
        assert step.source == DataSource.CRUNCHBASE
        assert step.action == "search_funding"
        assert step.params["investment_type"] == "series_b"
        assert step.depends_on == []

    def test_plan_step_json_serialization(self):
        """Test PlanStep can be serialized to/from JSON."""
        step = PlanStep(
            step_id=2,
            source=DataSource.COMPANIES_HOUSE,
            action="get_directors",
            params={"company_number": "12345678"},
            reason="Get company directors",
            depends_on=[1]
        )

        # Serialize to JSON
        json_str = step.model_dump_json()
        data = json.loads(json_str)

        assert data["step_id"] == 2
        assert data["source"] == "companies_house"
        assert data["depends_on"] == [1]

        # Deserialize from JSON
        step_from_json = PlanStep.model_validate_json(json_str)
        assert step_from_json.step_id == step.step_id
        assert step_from_json.source == step.source

    def test_clarification_request(self):
        """Test ClarificationRequest model."""
        clarification = ClarificationRequest(
            question="Which region would you like to focus on?",
            options=["London", "Manchester", "All UK"],
            context="The query is too broad without region filtering"
        )

        assert "region" in clarification.question.lower()
        assert len(clarification.options) == 3
        assert clarification.options[0] == "London"

    def test_execution_plan(self):
        """Test ExecutionPlan model."""
        steps = [
            PlanStep(
                step_id=1,
                source=DataSource.CRUNCHBASE,
                action="search_funding",
                params={},
                reason="Find funding rounds"
            ),
            PlanStep(
                step_id=2,
                source=DataSource.INTERNAL_CRM,
                action="check_clients",
                params={},
                reason="Exclude existing clients",
                depends_on=[1]
            )
        ]

        plan = ExecutionPlan(
            reasoning="Query Crunchbase first, then check CRM",
            steps=steps,
            clarification_needed=None,
            estimated_sources=2,
            confidence=0.85
        )

        assert len(plan.steps) == 2
        assert plan.estimated_sources == 2
        assert 0 <= plan.confidence <= 1
        assert plan.clarification_needed is None

    def test_execution_plan_json_roundtrip(self):
        """Test ExecutionPlan JSON serialization roundtrip."""
        plan = ExecutionPlan(
            reasoning="Test plan",
            steps=[
                PlanStep(
                    step_id=1,
                    source=DataSource.ORBIS,
                    action="search_companies",
                    params={"country": "GB"},
                    reason="Find UK companies"
                )
            ],
            estimated_sources=1,
            confidence=0.9
        )

        json_str = plan.model_dump_json()
        plan_from_json = ExecutionPlan.model_validate_json(json_str)

        assert plan_from_json.reasoning == plan.reasoning
        assert len(plan_from_json.steps) == 1
        assert plan_from_json.confidence == plan.confidence


class TestResultModels:
    """Tests for result-related models."""

    def test_search_result_success(self):
        """Test SearchResult for successful query."""
        result = SearchResult(
            step_id=1,
            source=DataSource.CRUNCHBASE,
            success=True,
            data={"count": 15, "results": []},
            error=None,
            record_count=15,
            execution_time_ms=342
        )

        assert result.success is True
        assert result.error is None
        assert result.record_count == 15
        assert isinstance(result.timestamp, datetime)

    def test_search_result_failure(self):
        """Test SearchResult for failed query."""
        result = SearchResult(
            step_id=1,
            source=DataSource.PITCHBOOK,
            success=False,
            data=None,
            error="API timeout after 30s",
            record_count=0,
            execution_time_ms=30000
        )

        assert result.success is False
        assert result.error is not None
        assert result.record_count == 0

    def test_search_result_json_serialization(self):
        """Test SearchResult JSON serialization."""
        result = SearchResult(
            step_id=1,
            source=DataSource.WEALTHX,
            success=True,
            data=[{"name": "John Smith", "net_worth": 85000000}],
            record_count=1,
            execution_time_ms=250
        )

        json_str = result.model_dump_json()
        result_from_json = SearchResult.model_validate_json(json_str)

        assert result_from_json.source == DataSource.WEALTHX
        assert result_from_json.record_count == 1
        assert isinstance(result_from_json.data, list)

    def test_aggregated_results(self):
        """Test AggregatedResults model."""
        plan = ExecutionPlan(
            reasoning="Test",
            steps=[],
            estimated_sources=1,
            confidence=0.8
        )

        results = AggregatedResults(
            original_query="Find UK tech companies",
            plan=plan,
            results=[],
            companies=[],
            individuals=[],
            total_records=0,
            sources_queried=[DataSource.CRUNCHBASE],
            execution_time_ms=1000
        )

        assert results.original_query == "Find UK tech companies"
        assert len(results.sources_queried) == 1
        assert results.execution_time_ms == 1000


class TestProspectModels:
    """Tests for prospect entity models."""

    def test_role_creation(self):
        """Test Role model."""
        role = Role(
            company_name="ACME Technologies Ltd",
            company_id="GB12345678",
            title="Chief Executive Officer",
            role_type="Executive",
            start_date="2018-03-15",
            end_date=None,
            is_current=True
        )

        assert role.company_name == "ACME Technologies Ltd"
        assert role.is_current is True
        assert role.end_date is None

    def test_company_creation(self):
        """Test Company model with comprehensive data."""
        company = Company(
            id="comp_001",
            name="ACME TECHNOLOGIES LTD",
            bvd_id="GB12345678",
            companies_house_number="12345678",
            crunchbase_uuid="abc-123",
            country="GB",
            city="London",
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
            investors=["Sequoia Capital", "Index Ventures"],
            sources=[DataSource.CRUNCHBASE, DataSource.COMPANIES_HOUSE]
        )

        assert company.name == "ACME TECHNOLOGIES LTD"
        assert company.country == "GB"
        assert company.revenue == 15000000
        assert company.employee_count == 85
        assert len(company.investors) == 2
        assert DataSource.CRUNCHBASE in company.sources

    def test_company_json_roundtrip(self):
        """Test Company JSON serialization roundtrip."""
        company = Company(
            id="comp_002",
            name="Test Company Ltd",
            country="GB",
            status="Active",
            sources=[DataSource.ORBIS]
        )

        json_str = company.model_dump_json()
        company_from_json = Company.model_validate_json(json_str)

        assert company_from_json.id == company.id
        assert company_from_json.name == company.name
        assert company_from_json.sources == company.sources

    def test_individual_creation(self):
        """Test Individual model with comprehensive data."""
        individual = Individual(
            id="ind_001",
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
                    title="CEO",
                    is_current=True
                )
            ],
            net_worth=85000000,
            net_worth_currency="USD",
            wealth_source="Self-made",
            liquidity=25000000,
            interests=["Technology", "Philanthropy"],
            philanthropy=["Education", "Climate change"],
            sources=[DataSource.WEALTHX, DataSource.COMPANIES_HOUSE],
            is_existing_client=False
        )

        assert individual.name == "John David Smith"
        assert individual.net_worth == 85000000
        assert len(individual.current_roles) == 1
        assert individual.current_roles[0].title == "CEO"
        assert "Technology" in individual.interests
        assert individual.is_existing_client is False

    def test_individual_json_roundtrip(self):
        """Test Individual JSON serialization roundtrip."""
        individual = Individual(
            id="ind_002",
            name="Jane Doe",
            country_of_residence="United Kingdom",
            net_worth=50000000,
            sources=[DataSource.WEALTH_MONITOR]
        )

        json_str = individual.model_dump_json()
        individual_from_json = Individual.model_validate_json(json_str)

        assert individual_from_json.id == individual.id
        assert individual_from_json.name == individual.name
        assert individual_from_json.net_worth == individual.net_worth

    def test_individual_with_roles(self):
        """Test Individual with multiple roles (current and previous)."""
        individual = Individual(
            id="ind_003",
            name="Alice Johnson",
            current_roles=[
                Role(
                    company_name="TechCorp",
                    title="CTO",
                    role_type="Executive",
                    is_current=True,
                    start_date="2020-01-01"
                )
            ],
            previous_roles=[
                Role(
                    company_name="OldCompany",
                    title="VP Engineering",
                    role_type="Executive",
                    is_current=False,
                    start_date="2015-01-01",
                    end_date="2019-12-31"
                )
            ],
            sources=[DataSource.COMPANIES_HOUSE]
        )

        assert len(individual.current_roles) == 1
        assert len(individual.previous_roles) == 1
        assert individual.current_roles[0].is_current is True
        assert individual.previous_roles[0].is_current is False
        assert individual.previous_roles[0].end_date is not None


class TestModelIntegration:
    """Integration tests for models working together."""

    def test_aggregated_results_with_all_entities(self):
        """Test AggregatedResults with companies and individuals."""
        # Create plan
        plan = ExecutionPlan(
            reasoning="Full integration test",
            steps=[
                PlanStep(
                    step_id=1,
                    source=DataSource.CRUNCHBASE,
                    action="search",
                    params={},
                    reason="Test"
                )
            ],
            estimated_sources=3,
            confidence=0.9
        )

        # Create company
        company = Company(
            id="comp_001",
            name="Test Corp",
            country="GB",
            sources=[DataSource.CRUNCHBASE]
        )

        # Create individual
        individual = Individual(
            id="ind_001",
            name="Test Person",
            current_roles=[
                Role(
                    company_name="Test Corp",
                    company_id="comp_001",
                    title="CEO",
                    is_current=True
                )
            ],
            sources=[DataSource.WEALTHX]
        )

        # Create search result
        search_result = SearchResult(
            step_id=1,
            source=DataSource.CRUNCHBASE,
            success=True,
            data={"test": "data"},
            record_count=1,
            execution_time_ms=100
        )

        # Create aggregated results
        aggregated = AggregatedResults(
            original_query="Test query",
            plan=plan,
            results=[search_result],
            companies=[company],
            individuals=[individual],
            total_records=2,
            sources_queried=[DataSource.CRUNCHBASE, DataSource.WEALTHX],
            execution_time_ms=500
        )

        # Verify structure
        assert len(aggregated.companies) == 1
        assert len(aggregated.individuals) == 1
        assert len(aggregated.results) == 1
        assert aggregated.total_records == 2

        # Test JSON serialization
        json_str = aggregated.model_dump_json()
        aggregated_from_json = AggregatedResults.model_validate_json(json_str)

        assert len(aggregated_from_json.companies) == 1
        assert len(aggregated_from_json.individuals) == 1
        assert aggregated_from_json.companies[0].name == "Test Corp"
        assert aggregated_from_json.individuals[0].name == "Test Person"
        assert aggregated_from_json.individuals[0].current_roles[0].company_id == "comp_001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
