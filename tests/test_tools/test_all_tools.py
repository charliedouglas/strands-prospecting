"""
Test suite for all data source tools.

Tests that each tool returns valid data matching expected schemas.
"""

import pytest
import asyncio
from src.tools import (
    # Orbis
    orbis_search_companies,
    orbis_get_directors,
    orbis_get_ownership,
    # Crunchbase
    crunchbase_search_funding_rounds,
    crunchbase_get_organization,
    # PitchBook
    pitchbook_search_deals,
    pitchbook_get_company,
    # Companies House
    companies_house_search,
    companies_house_get_company,
    companies_house_get_officers,
    companies_house_get_pscs,
    # Wealth-X
    wealthx_search_profiles,
    wealthx_get_profile,
    # Wealth Monitor
    wealth_monitor_search,
    # D&B
    dnb_match_company,
    dnb_get_company_data,
    # SerpAPI
    serpapi_news_search,
    serpapi_web_search,
    # Internal CRM
    crm_check_clients,
    crm_get_exclusions,
)


class TestOrbisTools:
    """Tests for Orbis (Bureau van Dijk) tools."""

    @pytest.mark.asyncio
    async def test_orbis_search_companies(self):
        """Test searching for companies in Orbis."""
        result = await orbis_search_companies(country="GB", status="Active")

        assert "total_count" in result
        assert "results" in result
        assert isinstance(result["results"], list)
        assert result["total_count"] > 0

        # Check first result structure
        if result["results"]:
            company = result["results"][0]
            assert "bvd_id" in company
            assert "name" in company
            assert "country" in company
            assert company["country"] == "GB"

    @pytest.mark.asyncio
    async def test_orbis_get_directors(self):
        """Test getting directors for a company."""
        result = await orbis_get_directors(bvd_id="GB12345678")

        assert "bvd_id" in result
        assert "company_name" in result
        assert "directors" in result
        assert isinstance(result["directors"], list)
        assert len(result["directors"]) > 0

        # Check director structure
        director = result["directors"][0]
        assert "name" in director
        assert "role" in director
        assert "is_current" in director

    @pytest.mark.asyncio
    async def test_orbis_get_ownership(self):
        """Test getting ownership structure."""
        result = await orbis_get_ownership(bvd_id="GB12345678")

        assert "bvd_id" in result
        assert "company_name" in result
        assert "shareholders" in result
        assert "ultimate_owner" in result
        assert isinstance(result["shareholders"], list)


class TestCrunchbaseTools:
    """Tests for Crunchbase tools."""

    @pytest.mark.asyncio
    async def test_crunchbase_search_funding_rounds(self):
        """Test searching for funding rounds."""
        result = await crunchbase_search_funding_rounds(investment_type="series_b")

        assert "count" in result
        assert "entities" in result
        assert isinstance(result["entities"], list)

        if result["entities"]:
            round_data = result["entities"][0]
            assert "properties" in round_data
            assert "investment_type" in round_data["properties"]

    @pytest.mark.asyncio
    async def test_crunchbase_get_organization(self):
        """Test getting organization details."""
        result = await crunchbase_get_organization(permalink="acme-technologies")

        assert "properties" in result
        props = result["properties"]
        assert "identifier" in props
        assert "short_description" in props
        assert "funding_total" in props


class TestPitchBookTools:
    """Tests for PitchBook tools."""

    @pytest.mark.asyncio
    async def test_pitchbook_search_deals(self):
        """Test searching for deals."""
        result = await pitchbook_search_deals(deal_type=["VC"], countries=["United Kingdom"])

        assert "total_count" in result
        assert "deals" in result
        assert isinstance(result["deals"], list)

        if result["deals"]:
            deal = result["deals"][0]
            assert "deal_id" in deal
            assert "deal_type" in deal
            assert "company" in deal

    @pytest.mark.asyncio
    async def test_pitchbook_get_company(self):
        """Test getting company profile."""
        result = await pitchbook_get_company(company_id="PB-CO-789012")

        assert "company_id" in result
        assert "name" in result
        assert "total_raised" in result
        assert "executives" in result


class TestCompaniesHouseTools:
    """Tests for Companies House tools."""

    @pytest.mark.asyncio
    async def test_companies_house_search(self):
        """Test searching for companies."""
        result = await companies_house_search(query="ACME")

        assert "items_per_page" in result
        assert "total_results" in result
        assert "items" in result
        assert isinstance(result["items"], list)

    @pytest.mark.asyncio
    async def test_companies_house_get_company(self):
        """Test getting company profile."""
        result = await companies_house_get_company(company_number="12345678")

        assert "company_number" in result
        assert "company_name" in result
        assert "company_status" in result
        assert "registered_office_address" in result

    @pytest.mark.asyncio
    async def test_companies_house_get_officers(self):
        """Test getting company officers."""
        result = await companies_house_get_officers(company_number="12345678")

        assert "total_results" in result
        assert "items" in result
        assert isinstance(result["items"], list)

        if result["items"]:
            officer = result["items"][0]
            assert "name" in officer
            assert "officer_role" in officer

    @pytest.mark.asyncio
    async def test_companies_house_get_pscs(self):
        """Test getting PSCs."""
        result = await companies_house_get_pscs(company_number="12345678")

        assert "total_results" in result
        assert "items" in result
        assert isinstance(result["items"], list)

        if result["items"]:
            psc = result["items"][0]
            assert "name" in psc
            assert "natures_of_control" in psc


class TestWealthXTools:
    """Tests for Wealth-X tools."""

    @pytest.mark.asyncio
    async def test_wealthx_search_profiles(self):
        """Test searching for UHNW profiles."""
        result = await wealthx_search_profiles(net_worth_min=50000000)

        assert "total_count" in result
        assert "profiles" in result
        assert isinstance(result["profiles"], list)

        if result["profiles"]:
            profile = result["profiles"][0]
            assert "wealthx_id" in profile
            assert "name" in profile
            assert "net_worth" in profile

    @pytest.mark.asyncio
    async def test_wealthx_get_profile(self):
        """Test getting specific profile."""
        result = await wealthx_get_profile(wealthx_id="WX-123456")

        assert "wealthx_id" in result
        assert "name" in result
        assert "net_worth" in result
        assert "interests" in result


class TestWealthMonitorTools:
    """Tests for Wealth Monitor tools."""

    @pytest.mark.asyncio
    async def test_wealth_monitor_search(self):
        """Test searching UK wealth data."""
        result = await wealth_monitor_search(region="London")

        assert "total_count" in result
        assert "individuals" in result
        assert isinstance(result["individuals"], list)


class TestDunBradstreetTools:
    """Tests for Dun & Bradstreet tools."""

    @pytest.mark.asyncio
    async def test_dnb_match_company(self):
        """Test matching a company."""
        result = await dnb_match_company(name="ACME Technologies", country="GB")

        assert "matchCandidates" in result
        assert "matchStatus" in result
        assert result["matchStatus"] == "success"

    @pytest.mark.asyncio
    async def test_dnb_get_company_data(self):
        """Test getting company data."""
        result = await dnb_get_company_data(duns_number="123456789")

        assert "organization" in result
        org = result["organization"]
        assert "duns" in org
        assert "primaryName" in org


class TestSerpAPITools:
    """Tests for SerpAPI tools."""

    @pytest.mark.asyncio
    async def test_serpapi_news_search(self):
        """Test news search."""
        result = await serpapi_news_search(query="ACME Technologies")

        assert "search_metadata" in result
        assert "news_results" in result
        assert isinstance(result["news_results"], list)

    @pytest.mark.asyncio
    async def test_serpapi_web_search(self):
        """Test web search."""
        result = await serpapi_web_search(query="Green Energy Solutions")

        assert "search_metadata" in result
        assert "organic_results" in result
        assert isinstance(result["organic_results"], list)


class TestInternalCRMTools:
    """Tests for Internal CRM tools."""

    @pytest.mark.asyncio
    async def test_crm_check_clients(self):
        """Test checking client status."""
        result = await crm_check_clients(
            individuals=[{"name": "Jane Doe"}],
            companies=[{"name": "Test Corp"}]
        )

        assert "matches" in result
        assert "individuals" in result["matches"]
        assert "companies" in result["matches"]
        assert isinstance(result["matches"]["individuals"], list)

    @pytest.mark.asyncio
    async def test_crm_get_exclusions(self):
        """Test getting exclusion list."""
        result = await crm_get_exclusions()

        assert "individuals" in result
        assert "companies" in result
        assert isinstance(result["individuals"], list)
        assert isinstance(result["companies"], list)


class TestToolsIntegration:
    """Integration tests across multiple tools."""

    @pytest.mark.asyncio
    async def test_company_workflow(self):
        """Test a complete company research workflow."""
        # 1. Search Companies House
        ch_result = await companies_house_search(query="ACME")
        assert len(ch_result["items"]) > 0

        company_number = ch_result["items"][0]["company_number"]

        # 2. Get company details
        company_details = await companies_house_get_company(company_number=company_number)
        assert company_details["company_number"] == company_number

        # 3. Get officers
        officers = await companies_house_get_officers(company_number=company_number)
        assert len(officers["items"]) > 0

        # 4. Check CRM
        crm_result = await crm_check_clients(
            companies=[{"name": company_details["company_name"]}]
        )
        assert len(crm_result["matches"]["companies"]) > 0

    @pytest.mark.asyncio
    async def test_individual_workflow(self):
        """Test a complete individual research workflow."""
        # 1. Search Wealth-X
        wx_result = await wealthx_search_profiles(net_worth_min=50000000)
        assert len(wx_result["profiles"]) > 0

        profile = wx_result["profiles"][0]

        # 2. Get full profile
        full_profile = await wealthx_get_profile(wealthx_id=profile["wealthx_id"])
        assert full_profile["wealthx_id"] == profile["wealthx_id"]

        # 3. Check CRM
        crm_result = await crm_check_clients(
            individuals=[{"name": profile["name"]}]
        )
        assert len(crm_result["matches"]["individuals"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
