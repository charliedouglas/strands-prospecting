"""
PitchBook mock API tools.

Provides access to PE/VC deals, private valuations, and investor networks.
"""

import logging
from typing import Optional
from strands import tool

from .base import load_mock_data, simulate_api_latency

logger = logging.getLogger(__name__)


@tool
async def pitchbook_search_deals(
    deal_type: Optional[list[str]] = None,
    regions: Optional[list[str]] = None,
    countries: Optional[list[str]] = None,
    industries: Optional[list[str]] = None,
    deal_size_min: Optional[float] = None,
    deal_size_max: Optional[float] = None,
    deal_date_min: Optional[str] = None,
    series: Optional[list[str]] = None,
    limit: int = 50
) -> dict:
    """
    Search for PE/VC deals in the PitchBook database.

    This tool searches PitchBook for private equity and venture capital deals
    including valuations, deal size, and investor information.

    Args:
        deal_type: List of deal types (e.g., ["VC", "PE Growth"])
        regions: List of regions to filter by
        countries: List of countries to filter by
        industries: List of industries to filter by
        deal_size_min: Minimum deal size in original currency
        deal_size_max: Maximum deal size in original currency
        deal_date_min: Minimum deal date (ISO format: "YYYY-MM-DD")
        series: List of funding series (e.g., ["B", "C"])
        limit: Maximum number of results (default: 50)

    Returns:
        Dictionary containing:
        - total_count: Number of matching deals
        - deals: List of deal records with company and investor details
    """
    logger.info(f"PitchBook: Searching deals with deal_type={deal_type}, countries={countries}")

    latency_ms = await simulate_api_latency()

    try:
        data = load_mock_data("pitchbook", "deals")
        deals = data["deals"]

        # Apply filters
        if deal_type:
            deals = [d for d in deals if d.get("deal_type") in deal_type]

        if countries:
            deals = [
                d for d in deals
                if any(country in d.get("company", {}).get("hq_location", "") for country in countries)
            ]

        if industries:
            deals = [
                d for d in deals
                if d.get("company", {}).get("primary_industry") in industries
            ]

        if deal_size_min is not None:
            deals = [d for d in deals if d.get("deal_size", 0) >= deal_size_min]

        if deal_size_max is not None:
            deals = [d for d in deals if d.get("deal_size", float('inf')) <= deal_size_max]

        if deal_date_min:
            deals = [d for d in deals if d.get("deal_date", "") >= deal_date_min]

        if series:
            deals = [
                d for d in deals
                if any(s in d.get("series", "") for s in series)
            ]

        deals = deals[:limit]

        logger.info(f"PitchBook: Found {len(deals)} deals")

        return {
            "total_count": len(deals),
            "deals": deals
        }

    except Exception as e:
        logger.error(f"PitchBook search error: {e}")
        return {
            "total_count": 0,
            "deals": [],
            "error": str(e)
        }


@tool
async def pitchbook_get_company(company_id: str) -> dict:
    """
    Get detailed company profile from PitchBook.

    Retrieves comprehensive company information including financials,
    funding history, executives, and ownership status.

    Args:
        company_id: PitchBook company ID (e.g., "PB-CO-789012")

    Returns:
        Dictionary containing full company profile with funding and valuation data
    """
    logger.info(f"PitchBook: Getting company {company_id}")

    latency_ms = await simulate_api_latency()

    try:
        data = load_mock_data("pitchbook", "companies")

        if company_id not in data:
            logger.warning(f"PitchBook: Company {company_id} not found")
            return {"error": f"Company {company_id} not found"}

        result = data[company_id]
        logger.info(f"PitchBook: Found company {company_id}")

        return result

    except Exception as e:
        logger.error(f"PitchBook get company error: {e}")
        return {"error": str(e)}
