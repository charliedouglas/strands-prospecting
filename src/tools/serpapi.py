"""
SerpAPI mock API tools.

Provides news search and web search functionality.
"""

import logging
from typing import Optional
from strands import tool

from .base import load_mock_data, simulate_api_latency

logger = logging.getLogger(__name__)


@tool
async def serpapi_news_search(query: str, gl: str = "uk") -> dict:
    """
    Search for news articles using Google News via SerpAPI.

    This tool searches for recent news articles related to companies,
    funding announcements, and business events.

    Args:
        query: Search query (e.g., "ACME Technologies funding")
        gl: Country code for localized results (default: "uk")

    Returns:
        Dictionary containing:
        - news_results: List of news articles with titles, links, and snippets
        - search_metadata: Metadata about the search
    """
    logger.info(f"SerpAPI: News search for query='{query}'")

    latency_ms = await simulate_api_latency()

    try:
        data = load_mock_data("serpapi", "news")

        # Simple keyword matching
        news_results = []
        for key, value in data.items():
            if any(word.lower() in query.lower() for word in key.split()):
                news_results.extend(value.get("news_results", []))

        if not news_results:
            # Return empty results if no matches
            news_results = []

        logger.info(f"SerpAPI: Found {len(news_results)} news results")

        return {
            "search_metadata": {
                "status": "Success",
                "query": query
            },
            "news_results": news_results
        }

    except Exception as e:
        logger.error(f"SerpAPI news search error: {e}")
        return {
            "search_metadata": {"status": "Error"},
            "news_results": [],
            "error": str(e)
        }


@tool
async def serpapi_web_search(query: str) -> dict:
    """
    Search the web using Google Search via SerpAPI.

    This tool performs general web searches for company information,
    websites, and general business intelligence.

    Args:
        query: Search query

    Returns:
        Dictionary containing:
        - organic_results: List of web search results
        - knowledge_graph: Knowledge graph information if available
    """
    logger.info(f"SerpAPI: Web search for query='{query}'")

    latency_ms = await simulate_api_latency()

    try:
        # Return mock web results
        return {
            "search_metadata": {
                "status": "Success",
                "query": query
            },
            "organic_results": [
                {
                    "position": 1,
                    "title": f"{query} | Official Website",
                    "link": f"https://{query.lower().replace(' ', '')}.com",
                    "snippet": f"Official website of {query}..."
                }
            ],
            "knowledge_graph": {
                "title": query,
                "type": "Company",
                "description": f"Information about {query}"
            }
        }

    except Exception as e:
        logger.error(f"SerpAPI web search error: {e}")
        return {
            "search_metadata": {"status": "Error"},
            "organic_results": [],
            "error": str(e)
        }
