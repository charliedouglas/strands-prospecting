"""
Data source tools for the prospecting agent.

This module exports all mock API tools for use with the Strands agent framework.
Each tool is decorated with @tool and can be used by agents to query data sources.
"""

# Import all tools
from .orbis import (
    orbis_search_companies,
    orbis_get_directors,
    orbis_get_ownership,
)

from .crunchbase import (
    crunchbase_search_funding_rounds,
    crunchbase_get_organization,
)

from .pitchbook import (
    pitchbook_search_deals,
    pitchbook_get_company,
)

from .companies_house import (
    companies_house_search,
    companies_house_get_company,
    companies_house_get_officers,
    companies_house_get_pscs,
)

from .wealthx import (
    wealthx_search_profiles,
    wealthx_get_profile,
)

from .wealth_monitor import (
    wealth_monitor_search,
)

from .dun_bradstreet import (
    dnb_match_company,
    dnb_get_company_data,
)

from .serpapi import (
    serpapi_news_search,
    serpapi_web_search,
)

from .internal_crm import (
    crm_check_clients,
    crm_get_exclusions,
)

# List of all available tools for Strands agents
ALL_TOOLS = [
    # Orbis (Bureau van Dijk)
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
    # Dun & Bradstreet
    dnb_match_company,
    dnb_get_company_data,
    # SerpAPI
    serpapi_news_search,
    serpapi_web_search,
    # Internal CRM
    crm_check_clients,
    crm_get_exclusions,
]

__all__ = [
    "ALL_TOOLS",
    # Orbis
    "orbis_search_companies",
    "orbis_get_directors",
    "orbis_get_ownership",
    # Crunchbase
    "crunchbase_search_funding_rounds",
    "crunchbase_get_organization",
    # PitchBook
    "pitchbook_search_deals",
    "pitchbook_get_company",
    # Companies House
    "companies_house_search",
    "companies_house_get_company",
    "companies_house_get_officers",
    "companies_house_get_pscs",
    # Wealth-X
    "wealthx_search_profiles",
    "wealthx_get_profile",
    # Wealth Monitor
    "wealth_monitor_search",
    # Dun & Bradstreet
    "dnb_match_company",
    "dnb_get_company_data",
    # SerpAPI
    "serpapi_news_search",
    "serpapi_web_search",
    # Internal CRM
    "crm_check_clients",
    "crm_get_exclusions",
]
