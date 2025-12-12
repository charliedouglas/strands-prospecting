"""
Wealth Monitor (UK) mock API tools.

Provides UK-specific wealth data, property portfolios, and shareholdings.
"""

import logging
from typing import Optional
from strands import tool

from .base import load_mock_data, simulate_api_latency

logger = logging.getLogger(__name__)


@tool
async def wealth_monitor_search(
    name: Optional[str] = None,
    region: Optional[str] = None,
    min_net_worth: Optional[float] = None,
    include_property: bool = True,
    include_shareholdings: bool = True
) -> dict:
    """
    Search for UK wealth data in Wealth Monitor database.

    This tool provides UK-specific wealth information including property
    portfolios, shareholdings, and directorships.

    Args:
        name: Individual name to search for
        region: UK region to filter by (e.g., "London", "Manchester")
        min_net_worth: Minimum net worth in GBP
        include_property: Include property portfolio data
        include_shareholdings: Include shareholding data

    Returns:
        Dictionary containing:
        - total_count: Number of matching individuals
        - individuals: List of wealth profiles with UK-specific data
    """
    logger.info(f"Wealth Monitor: Searching for name={name}, region={region}")

    latency_ms = await simulate_api_latency()

    try:
        data = load_mock_data("wealth_monitor", "individuals")
        individuals = data["individuals"]

        # Apply filters
        if name:
            individuals = [
                i for i in individuals
                if name.upper() in i.get("name", "").upper()
            ]

        if region:
            individuals = [
                i for i in individuals
                if i.get("region", "").upper() == region.upper()
            ]

        if min_net_worth is not None:
            individuals = [
                i for i in individuals
                if i.get("estimated_net_worth_gbp", 0) >= min_net_worth
            ]

        logger.info(f"Wealth Monitor: Found {len(individuals)} individuals")

        return {
            "total_count": len(individuals),
            "individuals": individuals
        }

    except Exception as e:
        logger.error(f"Wealth Monitor search error: {e}")
        return {
            "total_count": 0,
            "individuals": [],
            "error": str(e)
        }
