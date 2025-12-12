"""
Wealth-X mock API tools.

Provides access to UHNW profiles, wealth composition, interests, and connections.
"""

import logging
from typing import Optional
from strands import tool

from .base import load_mock_data, simulate_api_latency

logger = logging.getLogger(__name__)


@tool
async def wealthx_search_profiles(
    net_worth_min: Optional[float] = None,
    countries: Optional[list[str]] = None,
    industries: Optional[list[str]] = None,
    interests: Optional[list[str]] = None,
    keywords: Optional[str] = None,
    limit: int = 50
) -> dict:
    """
    Search for UHNW individual profiles in Wealth-X database.

    This tool searches Wealth-X for high net worth individual profiles including
    wealth data, interests, and professional information.

    Args:
        net_worth_min: Minimum net worth in USD
        countries: List of ISO 2-letter country codes (e.g., ["GB", "US"])
        industries: List of industries to filter by
        interests: List of interests/hobbies to filter by
        keywords: Keywords to search in profile text
        limit: Maximum number of results (default: 50)

    Returns:
        Dictionary containing:
        - total_count: Number of matching profiles
        - profiles: List of UHNW individual profiles
    """
    logger.info(f"Wealth-X: Searching profiles with net_worth_min={net_worth_min}")

    latency_ms = await simulate_api_latency()

    try:
        data = load_mock_data("wealthx", "profiles")
        profiles = data["profiles"]

        # Apply filters
        if net_worth_min is not None:
            profiles = [
                p for p in profiles
                if p.get("net_worth", {}).get("value", 0) >= net_worth_min
            ]

        if countries:
            # Map country names to codes
            country_map = {"United Kingdom": "GB", "GB": "GB", "US": "US", "United States": "US"}
            profiles = [
                p for p in profiles
                if any(country_map.get(p.get("country_of_residence"), "") == c for c in countries)
            ]

        if industries:
            profiles = [
                p for p in profiles
                if p.get("primary_industry") in industries
            ]

        if interests:
            profiles = [
                p for p in profiles
                if any(interest in p.get("interests", []) for interest in interests)
            ]

        if keywords:
            profiles = [
                p for p in profiles
                if keywords.lower() in str(p).lower()
            ]

        profiles = profiles[:limit]

        logger.info(f"Wealth-X: Found {len(profiles)} profiles")

        return {
            "total_count": len(profiles),
            "profiles": profiles
        }

    except Exception as e:
        logger.error(f"Wealth-X search error: {e}")
        return {
            "total_count": 0,
            "profiles": [],
            "error": str(e)
        }


@tool
async def wealthx_get_profile(wealthx_id: str) -> dict:
    """
    Get detailed profile for a specific UHNW individual.

    Retrieves comprehensive wealth and lifestyle information for an individual.

    Args:
        wealthx_id: Wealth-X profile ID (e.g., "WX-123456")

    Returns:
        Dictionary containing full profile with wealth, interests, and connections
    """
    logger.info(f"Wealth-X: Getting profile {wealthx_id}")

    latency_ms = await simulate_api_latency()

    try:
        data = load_mock_data("wealthx", "profiles")
        profiles = data["profiles"]

        # Find matching profile
        for profile in profiles:
            if profile.get("wealthx_id") == wealthx_id:
                logger.info(f"Wealth-X: Found profile {wealthx_id}")
                return profile

        logger.warning(f"Wealth-X: Profile {wealthx_id} not found")
        return {"error": f"Profile {wealthx_id} not found"}

    except Exception as e:
        logger.error(f"Wealth-X get profile error: {e}")
        return {"error": str(e)}
