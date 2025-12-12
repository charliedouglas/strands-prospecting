"""
Crunchbase mock API tools.

Provides access to funding rounds, startup ecosystem data, and investor information.
"""

import logging
from typing import Optional
from strands import tool

from .base import (
    load_mock_data,
    simulate_api_latency,
)

logger = logging.getLogger(__name__)


@tool
async def crunchbase_search_funding_rounds(
    investment_type: Optional[str] = None,
    location: Optional[str] = None,
    announced_on_gte: Optional[str] = None,
    announced_on_lte: Optional[str] = None,
    min_amount_usd: Optional[float] = None,
    limit: int = 50
) -> dict:
    """
    Search for funding rounds in the Crunchbase database.

    This tool searches Crunchbase for funding round information including
    investment type, amounts, investors, and funded organizations.

    Args:
        investment_type: Type of investment (e.g., "series_a", "series_b", "seed")
        location: Location filter (e.g., "united-kingdom", "london")
        announced_on_gte: Minimum announcement date (ISO format: "YYYY-MM-DD")
        announced_on_lte: Maximum announcement date (ISO format: "YYYY-MM-DD")
        min_amount_usd: Minimum funding amount in USD
        limit: Maximum number of results (default: 50)

    Returns:
        Dictionary containing:
        - count: Number of matching funding rounds
        - entities: List of funding round records with details
    """
    logger.info(f"Crunchbase: Searching funding rounds - type={investment_type}, location={location}")

    # Simulate API latency
    latency_ms = await simulate_api_latency()

    try:
        # Load mock data
        data = load_mock_data("crunchbase", "funding_rounds")
        entities = data["entities"]

        # Apply filters
        if investment_type:
            entities = [
                e for e in entities
                if e["properties"].get("investment_type") == investment_type
            ]

        if location:
            entities = [
                e for e in entities
                if any(
                    location.lower() in loc.get("value", "").lower()
                    for loc in e["properties"].get("funded_organization_identifier", {}).get("location_identifiers", [])
                )
            ]

        if announced_on_gte:
            entities = [
                e for e in entities
                if e["properties"].get("announced_on", "") >= announced_on_gte
            ]

        if announced_on_lte:
            entities = [
                e for e in entities
                if e["properties"].get("announced_on", "") <= announced_on_lte
            ]

        if min_amount_usd is not None:
            entities = [
                e for e in entities
                if e["properties"].get("money_raised", {}).get("value_usd", 0) >= min_amount_usd
            ]

        # Apply limit
        entities = entities[:limit]

        logger.info(f"Crunchbase: Found {len(entities)} funding rounds")

        return {
            "count": len(entities),
            "entities": entities
        }

    except Exception as e:
        logger.error(f"Crunchbase search error: {e}")
        return {
            "count": 0,
            "entities": [],
            "error": str(e)
        }


@tool
async def crunchbase_get_organization(permalink: str) -> dict:
    """
    Get detailed information about a specific organization.

    Retrieves comprehensive organization data including description, funding,
    employees, location, and categories.

    Args:
        permalink: Crunchbase permalink/slug for the organization
                  (e.g., "acme-technologies", "fintech-innovations")

    Returns:
        Dictionary containing organization properties:
        - identifier: UUID and permalink
        - short_description: Company description
        - founded_on: Founding date
        - num_employees_enum: Employee count range
        - website: Company website
        - location_identifiers: Location information
        - categories: Business categories
        - funding_total: Total funding raised
    """
    logger.info(f"Crunchbase: Getting organization {permalink}")

    # Simulate API latency
    latency_ms = await simulate_api_latency()

    try:
        # Load mock data
        data = load_mock_data("crunchbase", "organizations")

        if permalink not in data:
            logger.warning(f"Crunchbase: Organization {permalink} not found")
            return {
                "error": f"Organization {permalink} not found"
            }

        result = data[permalink]
        logger.info(f"Crunchbase: Found organization {permalink}")

        return result

    except Exception as e:
        logger.error(f"Crunchbase get organization error: {e}")
        return {
            "error": str(e)
        }
