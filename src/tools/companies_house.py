"""
Companies House (UK) mock API tools.

Provides access to UK company filings, officers, and persons with significant control (PSCs).
"""

import logging
from typing import Optional
from strands import tool

from .base import load_mock_data, simulate_api_latency

logger = logging.getLogger(__name__)


@tool
async def companies_house_search(query: str, limit: int = 20) -> dict:
    """
    Search for UK companies in Companies House database.

    This tool searches the UK Companies House registry for company information.

    Args:
        query: Company name or number to search for
        limit: Maximum number of results (default: 20)

    Returns:
        Dictionary containing:
        - items_per_page: Number of items per page
        - total_results: Total number of matches
        - items: List of company records
    """
    logger.info(f"Companies House: Searching for '{query}'")

    latency_ms = await simulate_api_latency()

    try:
        data = load_mock_data("companies_house", "companies")
        items = data["items"]

        # Filter by query
        items = [
            item for item in items
            if query.upper() in item["title"].upper() or query in item["company_number"]
        ]

        items = items[:limit]

        logger.info(f"Companies House: Found {len(items)} companies")

        return {
            "items_per_page": limit,
            "total_results": len(items),
            "items": items
        }

    except Exception as e:
        logger.error(f"Companies House search error: {e}")
        return {
            "items_per_page": 0,
            "total_results": 0,
            "items": [],
            "error": str(e)
        }


@tool
async def companies_house_get_company(company_number: str) -> dict:
    """
    Get detailed company profile from Companies House.

    Retrieves full company information including registered address,
    SIC codes, and filing status.

    Args:
        company_number: UK Companies House number (e.g., "12345678")

    Returns:
        Dictionary containing full company profile
    """
    logger.info(f"Companies House: Getting company {company_number}")

    latency_ms = await simulate_api_latency()

    try:
        data = load_mock_data("companies_house", "profiles")

        if company_number not in data:
            logger.warning(f"Companies House: Company {company_number} not found")
            return {"error": f"Company {company_number} not found"}

        result = data[company_number]
        logger.info(f"Companies House: Found company {company_number}")

        return result

    except Exception as e:
        logger.error(f"Companies House get company error: {e}")
        return {"error": str(e)}


@tool
async def companies_house_get_officers(company_number: str) -> dict:
    """
    Get officers (directors) for a UK company.

    Retrieves list of current and resigned officers for a company.

    Args:
        company_number: UK Companies House number (e.g., "12345678")

    Returns:
        Dictionary containing:
        - items_per_page: Number of items
        - total_results: Total number of officers
        - items: List of officer records
    """
    logger.info(f"Companies House: Getting officers for {company_number}")

    latency_ms = await simulate_api_latency()

    try:
        data = load_mock_data("companies_house", "officers")

        if company_number not in data:
            logger.warning(f"Companies House: No officers found for {company_number}")
            return {
                "items_per_page": 0,
                "total_results": 0,
                "items": [],
                "error": f"Company {company_number} not found"
            }

        result = data[company_number]
        logger.info(f"Companies House: Found {result['total_results']} officers")

        return result

    except Exception as e:
        logger.error(f"Companies House get officers error: {e}")
        return {
            "items_per_page": 0,
            "total_results": 0,
            "items": [],
            "error": str(e)
        }


@tool
async def companies_house_get_pscs(company_number: str) -> dict:
    """
    Get Persons with Significant Control (PSCs) for a UK company.

    Retrieves information about individuals or entities with significant
    ownership or control over the company.

    Args:
        company_number: UK Companies House number (e.g., "12345678")

    Returns:
        Dictionary containing:
        - items_per_page: Number of items
        - total_results: Total number of PSCs
        - items: List of PSC records with ownership details
    """
    logger.info(f"Companies House: Getting PSCs for {company_number}")

    latency_ms = await simulate_api_latency()

    try:
        data = load_mock_data("companies_house", "pscs")

        if company_number not in data:
            logger.warning(f"Companies House: No PSCs found for {company_number}")
            return {
                "items_per_page": 0,
                "total_results": 0,
                "items": [],
                "error": f"Company {company_number} not found"
            }

        result = data[company_number]
        logger.info(f"Companies House: Found {result['total_results']} PSCs")

        return result

    except Exception as e:
        logger.error(f"Companies House get PSCs error: {e}")
        return {
            "items_per_page": 0,
            "total_results": 0,
            "items": [],
            "error": str(e)
        }
