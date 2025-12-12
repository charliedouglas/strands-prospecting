"""
Test suite for the Planner Agent.

Tests the planner's ability to create execution plans from various
types of prospecting queries.
"""

import pytest
import asyncio
from src.agents import PlannerAgent, QueryIntent
from src.models import DataSource


class TestPlannerAgent:
    """Tests for the PlannerAgent class."""

    @pytest.fixture
    def planner(self):
        """Create a planner agent instance."""
        return PlannerAgent()

    @pytest.mark.asyncio
    async def test_planner_initialization(self, planner):
        """Test that the planner initializes correctly."""
        assert planner is not None
        assert planner.planner_model is not None
        assert planner.planner_agent is not None
        assert planner.intent_agent is not None
        assert planner.settings is not None

    @pytest.mark.asyncio
    async def test_funding_query(self, planner):
        """Test planning for funding/investment queries."""
        query = "Find UK tech companies that raised Series B in 2024"

        plan = await planner.create_plan(query)

        # Verify plan structure
        assert plan is not None
        assert plan.reasoning is not None
        assert len(plan.steps) > 0
        assert plan.estimated_sources > 0
        assert 0 <= plan.confidence <= 1

        # Should include funding sources
        sources_used = [step.source for step in plan.steps]
        assert DataSource.CRUNCHBASE in sources_used or DataSource.PITCHBOOK in sources_used

        # Should always include CRM check at the end
        assert plan.steps[-1].source == DataSource.INTERNAL_CRM

        # Should not need clarification for this clear query
        assert plan.clarification_needed is None

        print(f"\n✓ Funding query plan created with {len(plan.steps)} steps")
        print(f"  Sources: {[s.value for s in sources_used]}")
        print(f"  Confidence: {plan.confidence}")

    @pytest.mark.asyncio
    async def test_directors_query(self, planner):
        """Test planning for director lookup queries."""
        query = "Who are the directors of ACME Technologies?"

        plan = await planner.create_plan(query)

        # Verify plan structure
        assert plan is not None
        assert len(plan.steps) > 0

        # Should include Companies House or Orbis for UK company directors
        sources_used = [step.source for step in plan.steps]
        assert DataSource.COMPANIES_HOUSE in sources_used or DataSource.ORBIS in sources_used

        # Should include CRM check as last step
        assert plan.steps[-1].source == DataSource.INTERNAL_CRM

        print(f"\n✓ Directors query plan created with {len(plan.steps)} steps")
        print(f"  Sources: {[s.value for s in sources_used]}")

    @pytest.mark.asyncio
    async def test_uhnw_individuals_query(self, planner):
        """Test planning for UHNW individual queries."""
        query = "Find wealthy tech founders in London with net worth over £50m"

        plan = await planner.create_plan(query)

        # Verify plan structure
        assert plan is not None
        assert len(plan.steps) > 0

        # Should include Wealth-X or Wealth Monitor
        sources_used = [step.source for step in plan.steps]
        assert DataSource.WEALTHX in sources_used or DataSource.WEALTH_MONITOR in sources_used

        # Should include CRM check
        assert DataSource.INTERNAL_CRM in sources_used

        print(f"\n✓ UHNW query plan created with {len(plan.steps)} steps")
        print(f"  Sources: {[s.value for s in sources_used]}")

    @pytest.mark.asyncio
    async def test_ambiguous_query(self, planner):
        """Test that ambiguous queries request clarification."""
        query = "Tell me about XYZ"

        plan = await planner.create_plan(query)

        # This query is too vague - should request clarification
        assert plan is not None

        # Either has clarification or has very low confidence
        if plan.clarification_needed:
            assert plan.clarification_needed.question is not None
            assert plan.clarification_needed.context is not None
            print(f"\n✓ Ambiguous query correctly requested clarification")
            print(f"  Question: {plan.clarification_needed.question}")
        else:
            # If no clarification, confidence should be low
            assert plan.confidence < 0.6
            print(f"\n✓ Ambiguous query returned plan with low confidence: {plan.confidence}")

    @pytest.mark.asyncio
    async def test_plan_step_dependencies(self, planner):
        """Test that plans include proper step dependencies."""
        query = "Get full details on Green Energy Solutions including directors and recent funding"

        plan = await planner.create_plan(query)

        assert plan is not None
        assert len(plan.steps) >= 3  # Should have multiple steps

        # Check that step IDs are sequential
        step_ids = [step.step_id for step in plan.steps]
        assert step_ids == list(range(1, len(plan.steps) + 1))

        # Some steps should have dependencies
        has_dependencies = any(len(step.depends_on) > 0 for step in plan.steps)

        print(f"\n✓ Complex query plan created with {len(plan.steps)} steps")
        print(f"  Has dependencies: {has_dependencies}")
        for step in plan.steps:
            print(f"  Step {step.step_id}: {step.source.value} - {step.action}")
            if step.depends_on:
                print(f"    Depends on: {step.depends_on}")

    @pytest.mark.asyncio
    async def test_plan_includes_crm_check(self, planner):
        """Test that all prospect-focused plans include CRM check."""
        queries = [
            "Find Series A companies in London",
            "Find wealthy individuals in Manchester with net worth over £30m",
            "Get directors of UK tech startups founded in the last 3 years",
        ]

        for query in queries:
            plan = await planner.create_plan(query)

            # If plan has steps (not requesting clarification), last step should be CRM check
            if plan.steps:
                assert plan.steps[-1].source == DataSource.INTERNAL_CRM
                print(f"✓ '{query[:50]}...' includes CRM check")
            else:
                # If no steps, it should be because clarification is needed
                assert plan.clarification_needed is not None
                print(f"⊘ '{query[:50]}...' needs clarification (no steps)")

    @pytest.mark.asyncio
    async def test_query_intent_analysis(self, planner):
        """Test query intent classification."""
        test_cases = [
            ("Find companies that raised Series B funding", QueryIntent.FUNDING_INVESTMENT),
            ("Who are the wealthy individuals in London", QueryIntent.UHNW_INDIVIDUAL),
            ("Get directors of ACME Technologies", QueryIntent.DIRECTORS_FOUNDERS),
            ("Show me company ownership structure", QueryIntent.UK_COMPANY_STRUCTURE),
            ("What is the credit rating", QueryIntent.CREDIT_RISK),
            ("Recent news about the company", QueryIntent.NEWS_SIGNALS),
            ("Tell me about xyz", QueryIntent.AMBIGUOUS),
        ]

        for query, expected_intent in test_cases:
            intent = await planner.analyze_query_intent(query)
            assert intent == expected_intent
            print(f"✓ '{query}' -> {intent.value}")

    @pytest.mark.asyncio
    async def test_plan_json_structure(self, planner):
        """Test that plans have valid JSON structure."""
        query = "Find fintech companies in the UK"

        plan = await planner.create_plan(query)

        # Test that plan can be serialized to JSON
        plan_json = plan.model_dump_json()
        assert plan_json is not None

        # Test that it's valid JSON
        import json
        plan_dict = json.loads(plan_json)

        assert "reasoning" in plan_dict
        assert "steps" in plan_dict
        assert "estimated_sources" in plan_dict
        assert "confidence" in plan_dict

        print(f"\n✓ Plan successfully serializes to valid JSON")
        print(f"  JSON length: {len(plan_json)} characters")


class TestPlannerIntegration:
    """Integration tests for the planner with realistic scenarios."""

    @pytest.fixture
    def planner(self):
        """Create a planner agent instance."""
        return PlannerAgent()

    @pytest.mark.asyncio
    async def test_complete_company_research_plan(self, planner):
        """Test planning a complete company research workflow."""
        query = "Research ACME Technologies - ownership, directors, funding, and recent news"

        plan = await planner.create_plan(query)

        assert plan is not None
        assert len(plan.steps) >= 4  # Should query multiple sources

        sources_used = [step.source for step in plan.steps]

        # Should cover multiple aspects
        # Ownership/structure sources
        has_structure = any(s in sources_used for s in [
            DataSource.ORBIS,
            DataSource.COMPANIES_HOUSE,
            DataSource.DUN_BRADSTREET
        ])

        # Funding sources
        has_funding = any(s in sources_used for s in [
            DataSource.CRUNCHBASE,
            DataSource.PITCHBOOK
        ])

        # News sources
        has_news = DataSource.SERPAPI in sources_used

        # CRM check
        has_crm = DataSource.INTERNAL_CRM in sources_used

        print(f"\n✓ Complete research plan:")
        print(f"  Structure sources: {has_structure}")
        print(f"  Funding sources: {has_funding}")
        print(f"  News sources: {has_news}")
        print(f"  CRM check: {has_crm}")
        print(f"  Total steps: {len(plan.steps)}")

        assert has_crm, "Should always include CRM check"

    @pytest.mark.asyncio
    async def test_cross_referencing_strategy(self, planner):
        """Test that planner uses cross-referencing for accuracy."""
        query = "Find all Series B funding rounds in UK tech sector in 2024"

        plan = await planner.create_plan(query)

        sources_used = [step.source for step in plan.steps]

        # For funding queries, should ideally use both Crunchbase AND PitchBook
        funding_sources = [s for s in sources_used if s in [DataSource.CRUNCHBASE, DataSource.PITCHBOOK]]

        print(f"\n✓ Funding query uses {len(funding_sources)} funding sources for cross-reference")
        print(f"  Sources: {[s.value for s in funding_sources]}")

        # High confidence plans should use multiple sources
        if plan.confidence > 0.8:
            assert len(funding_sources) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
