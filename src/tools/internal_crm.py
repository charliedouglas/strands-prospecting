"""
Internal CRM mock API tools.

Provides existing client checks and exclusion list management.
"""

import logging
from typing import Optional
from strands import tool

from .base import load_mock_data, simulate_api_latency

logger = logging.getLogger(__name__)


@tool
async def crm_check_clients(
    individuals: Optional[list[dict]] = None,
    companies: Optional[list[dict]] = None
) -> dict:
    """
    Check if individuals or companies are existing clients or prospects.

    This tool checks the internal CRM to identify existing relationships
    and exclusions before proceeding with prospecting.

    Args:
        individuals: List of individuals to check, each with 'name' and optionally 'company'
        companies: List of companies to check, each with 'name' and optionally 'company_number'

    Returns:
        Dictionary containing:
        - matches: Matching records with relationship status
            - individuals: List of individual matches
            - companies: List of company matches
    """
    logger.info(f"CRM: Checking {len(individuals or [])} individuals and {len(companies or [])} companies")

    latency_ms = await simulate_api_latency()

    try:
        data = load_mock_data("internal_crm", "clients")

        individual_matches = []
        company_matches = []

        # Check individuals
        if individuals:
            for ind in individuals:
                name = ind.get("name", "")
                if name in data.get("individuals", {}):
                    client_data = data["individuals"][name]
                    individual_matches.append({
                        "query_name": name,
                        **client_data
                    })
                else:
                    # Not in CRM
                    individual_matches.append({
                        "query_name": name,
                        "is_client": False,
                        "is_prospect": False,
                        "is_excluded": False,
                        "relationship_manager": None,
                        "notes": None
                    })

        # Check companies
        if companies:
            for comp in companies:
                name = comp.get("name", "")
                if name in data.get("companies", {}):
                    client_data = data["companies"][name]
                    company_matches.append({
                        "query_name": name,
                        **client_data
                    })
                else:
                    # Not in CRM
                    company_matches.append({
                        "query_name": name,
                        "is_client": False,
                        "is_prospect": False,
                        "is_excluded": False,
                        "notes": None
                    })

        logger.info(f"CRM: Found {len(individual_matches)} individual matches, {len(company_matches)} company matches")

        return {
            "matches": {
                "individuals": individual_matches,
                "companies": company_matches
            }
        }

    except Exception as e:
        logger.error(f"CRM check clients error: {e}")
        return {
            "matches": {
                "individuals": [],
                "companies": []
            },
            "error": str(e)
        }


@tool
async def crm_get_exclusions() -> dict:
    """
    Get the list of excluded individuals and companies.

    Retrieves individuals and companies that should be excluded from
    prospecting due to compliance concerns or other reasons.

    Returns:
        Dictionary containing:
        - individuals: List of excluded individuals with reasons
        - companies: List of excluded companies with reasons
    """
    logger.info("CRM: Getting exclusion list")

    latency_ms = await simulate_api_latency()

    try:
        data = load_mock_data("internal_crm", "clients")
        exclusions = data.get("exclusions", {"individuals": [], "companies": []})

        logger.info(f"CRM: Found {len(exclusions['individuals'])} excluded individuals, "
                   f"{len(exclusions['companies'])} excluded companies")

        return exclusions

    except Exception as e:
        logger.error(f"CRM get exclusions error: {e}")
        return {
            "individuals": [],
            "companies": [],
            "error": str(e)
        }
