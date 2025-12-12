"""
Orbis (Bureau van Dijk) mock API tools.

Provides access to corporate structures, financials, ownership, and directors.
"""

import logging
from typing import Optional
from strands import tool

from .base import (
    load_mock_data,
    get_mock_record_by_id,
    filter_mock_data,
    simulate_api_latency,
    create_success_response,
    create_error_response,
)

logger = logging.getLogger(__name__)


@tool
async def orbis_search_companies(
    name: Optional[str] = None,
    country: Optional[str] = None,
    city: Optional[str] = None,
    bvd_id: Optional[str] = None,
    national_id: Optional[str] = None,
    status: Optional[str] = "Active",
    min_revenue: Optional[float] = None,
    max_revenue: Optional[float] = None,
    min_employees: Optional[int] = None,
    max_employees: Optional[int] = None,
    limit: int = 100
) -> dict:
    """
    Search for companies in the Orbis database.

    This tool searches Bureau van Dijk's Orbis database for company information
    including financials, structure, and basic details.

    Args:
        name: Company name to search for (partial match)
        country: ISO 2-letter country code (e.g., "GB" for United Kingdom)
        city: City name
        bvd_id: Bureau van Dijk ID
        national_id: National registration number (e.g., Companies House number)
        status: Company status filter (default: "Active")
        min_revenue: Minimum revenue filter
        max_revenue: Maximum revenue filter
        min_employees: Minimum employee count
        max_employees: Maximum employee count
        limit: Maximum number of results (default: 100)

    Returns:
        Dictionary containing:
        - total_count: Total number of matching companies
        - results: List of company records with details
    """
    logger.info(f"Orbis: Searching companies with filters - name={name}, country={country}, city={city}")

    # Simulate API latency
    latency_ms = await simulate_api_latency()

    try:
        # Load mock data
        data = load_mock_data("orbis", "companies")
        results = data["results"]

        # Apply filters
        if name:
            results = [r for r in results if name.upper() in r["name"].upper()]

        if country:
            results = [r for r in results if r["country"] == country.upper()]

        if city:
            results = [r for r in results if r["registered_address"]["city"].upper() == city.upper()]

        if bvd_id:
            results = [r for r in results if r["bvd_id"] == bvd_id]

        if national_id:
            results = [
                r for r in results
                if any(nid["value"] == national_id for nid in r.get("national_ids", []))
            ]

        if status:
            results = [r for r in results if r["status"] == status]

        # Apply numeric filters
        if min_revenue is not None:
            results = [r for r in results if r.get("operating_revenue", 0) >= min_revenue]

        if max_revenue is not None:
            results = [r for r in results if r.get("operating_revenue", float('inf')) <= max_revenue]

        if min_employees is not None:
            results = [r for r in results if r.get("employees", 0) >= min_employees]

        if max_employees is not None:
            results = [r for r in results if r.get("employees", float('inf')) <= max_employees]

        # Apply limit
        results = results[:limit]

        logger.info(f"Orbis: Found {len(results)} companies")

        return {
            "total_count": len(results),
            "results": results
        }

    except Exception as e:
        logger.error(f"Orbis search error: {e}")
        return {
            "total_count": 0,
            "results": [],
            "error": str(e)
        }


@tool
async def orbis_get_directors(bvd_id: str) -> dict:
    """
    Get directors and officers for a specific company.

    Retrieves the list of current and past directors for a company identified
    by its Bureau van Dijk ID.

    Args:
        bvd_id: Bureau van Dijk company ID (e.g., "GB12345678")

    Returns:
        Dictionary containing:
        - bvd_id: Company BvD ID
        - company_name: Company name
        - directors: List of director records with appointment details
    """
    logger.info(f"Orbis: Getting directors for {bvd_id}")

    # Simulate API latency
    latency_ms = await simulate_api_latency()

    try:
        # Load mock data
        data = load_mock_data("orbis", "directors")

        if bvd_id not in data:
            logger.warning(f"Orbis: No directors found for {bvd_id}")
            return {
                "bvd_id": bvd_id,
                "company_name": None,
                "directors": [],
                "error": f"Company {bvd_id} not found"
            }

        result = data[bvd_id]
        logger.info(f"Orbis: Found {len(result['directors'])} directors for {bvd_id}")

        return result

    except Exception as e:
        logger.error(f"Orbis get directors error: {e}")
        return {
            "bvd_id": bvd_id,
            "company_name": None,
            "directors": [],
            "error": str(e)
        }


@tool
async def orbis_get_ownership(bvd_id: str) -> dict:
    """
    Get ownership structure for a specific company.

    Retrieves shareholder information and ultimate ownership structure
    for a company identified by its Bureau van Dijk ID.

    Args:
        bvd_id: Bureau van Dijk company ID (e.g., "GB12345678")

    Returns:
        Dictionary containing:
        - bvd_id: Company BvD ID
        - company_name: Company name
        - shareholders: List of shareholders with ownership percentages
        - ultimate_owner: Information about the ultimate beneficial owner
    """
    logger.info(f"Orbis: Getting ownership structure for {bvd_id}")

    # Simulate API latency
    latency_ms = await simulate_api_latency()

    try:
        # Load mock data
        data = load_mock_data("orbis", "ownership")

        if bvd_id not in data:
            logger.warning(f"Orbis: No ownership data found for {bvd_id}")
            return {
                "bvd_id": bvd_id,
                "company_name": None,
                "shareholders": [],
                "ultimate_owner": None,
                "error": f"Company {bvd_id} not found"
            }

        result = data[bvd_id]
        logger.info(f"Orbis: Found {len(result['shareholders'])} shareholders for {bvd_id}")

        return result

    except Exception as e:
        logger.error(f"Orbis get ownership error: {e}")
        return {
            "bvd_id": bvd_id,
            "company_name": None,
            "shareholders": [],
            "ultimate_owner": None,
            "error": str(e)
        }
