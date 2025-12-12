"""
Dun & Bradstreet (D&B Direct+) mock API tools.

Provides credit risk, business signals, and firmographics data.
"""

import logging
from typing import Optional
from strands import tool

from .base import load_mock_data, simulate_api_latency

logger = logging.getLogger(__name__)


@tool
async def dnb_match_company(
    name: str,
    country: str,
    city: Optional[str] = None
) -> dict:
    """
    Match and identify a company in the D&B database.

    This tool matches a company by name and location to find its DUNS number
    and basic information.

    Args:
        name: Company name to match
        country: ISO 2-letter country code (e.g., "GB")
        city: City name for more accurate matching (optional)

    Returns:
        Dictionary containing:
        - matchCandidates: List of potential matches with confidence scores
        - candidatesMatchedQuantity: Number of matches found
        - matchStatus: Status of the match operation
    """
    logger.info(f"D&B: Matching company name={name}, country={country}")

    latency_ms = await simulate_api_latency()

    try:
        # For mock purposes, return a simple match
        return {
            "matchCandidates": [
                {
                    "organization": {
                        "duns": "123456789",
                        "primaryName": name.upper(),
                        "dunsControlStatus": {
                            "operatingStatus": {"description": "Active"}
                        },
                        "primaryAddress": {
                            "addressLocality": {"name": city or "London"},
                            "addressCountry": {"isoAlpha2Code": country}
                        }
                    },
                    "matchQualityInformation": {
                        "confidenceCode": 10,
                        "matchGrade": "AAAAAAAAFFF",
                        "nameMatchScore": 100.0
                    }
                }
            ],
            "candidatesMatchedQuantity": 1,
            "matchStatus": "success"
        }

    except Exception as e:
        logger.error(f"D&B match error: {e}")
        return {
            "matchCandidates": [],
            "candidatesMatchedQuantity": 0,
            "matchStatus": "error",
            "error": str(e)
        }


@tool
async def dnb_get_company_data(duns_number: str) -> dict:
    """
    Get comprehensive company data from D&B.

    Retrieves detailed company information including financials, credit scores,
    principals, and corporate linkage.

    Args:
        duns_number: D&B DUNS number (e.g., "123456789")

    Returns:
        Dictionary containing:
        - organization: Company details including financials and employees
        - principals: List of company principals/directors
        - corporateLinkage: Corporate hierarchy information
    """
    logger.info(f"D&B: Getting company data for DUNS {duns_number}")

    latency_ms = await simulate_api_latency()

    try:
        data = load_mock_data("dun_bradstreet", "companies")

        if duns_number not in data:
            logger.warning(f"D&B: Company {duns_number} not found")
            return {"error": f"Company with DUNS {duns_number} not found"}

        result = data[duns_number]
        logger.info(f"D&B: Found company data for DUNS {duns_number}")

        return result

    except Exception as e:
        logger.error(f"D&B get company data error: {e}")
        return {"error": str(e)}
