"""
Base utilities for mock API tools.

This module provides common functionality for all data source tools,
including mock data loading, response structures, and error handling.
"""

import json
import random
import asyncio
import logging
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MockResponse:
    """
    Standardized response structure for mock API calls.

    Attributes:
        success: Whether the request succeeded
        data: Response data (can be dict, list, or None)
        error: Error message if request failed
        latency_ms: Simulated latency in milliseconds
    """
    success: bool
    data: Any
    error: Optional[str] = None
    latency_ms: int = 0


async def simulate_api_latency(min_ms: int = 100, max_ms: int = 500) -> None:
    """
    Simulate realistic API latency with random delay.

    Args:
        min_ms: Minimum latency in milliseconds
        max_ms: Maximum latency in milliseconds
    """
    latency_ms = random.randint(min_ms, max_ms)
    await asyncio.sleep(latency_ms / 1000.0)
    return latency_ms


def load_mock_data(source: str, filename: str) -> Any:
    """
    Load mock data from JSON file.

    Args:
        source: Data source name (e.g., "orbis", "crunchbase")
        filename: Name of the JSON file (without .json extension)

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If the mock data file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    # Get the project root (3 levels up from this file)
    project_root = Path(__file__).parent.parent.parent
    mock_file = project_root / "src" / "mocks" / "data" / source / f"{filename}.json"

    logger.debug(f"Loading mock data from {mock_file}")

    if not mock_file.exists():
        logger.error(f"Mock data file not found: {mock_file}")
        raise FileNotFoundError(f"Mock data file not found: {mock_file}")

    with open(mock_file, "r") as f:
        data = json.load(f)

    logger.debug(f"Loaded mock data for {source}/{filename}")
    return data


def get_mock_record_by_id(source: str, filename: str, id_field: str, id_value: str) -> Optional[dict]:
    """
    Get a specific record from mock data by ID.

    Args:
        source: Data source name
        filename: Name of the JSON file
        id_field: Name of the ID field to match
        id_value: Value of the ID to search for

    Returns:
        Matching record or None if not found
    """
    try:
        data = load_mock_data(source, filename)

        # Handle different data structures
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict) and "results" in data:
            records = data["results"]
        elif isinstance(data, dict) and "items" in data:
            records = data["items"]
        else:
            records = [data]

        for record in records:
            if record.get(id_field) == id_value:
                return record

        logger.warning(f"No record found with {id_field}={id_value} in {source}/{filename}")
        return None

    except Exception as e:
        logger.error(f"Error loading mock record: {e}")
        return None


def filter_mock_data(records: list[dict], filters: dict) -> list[dict]:
    """
    Filter mock data records based on provided filters.

    Args:
        records: List of records to filter
        filters: Dictionary of field_name: value pairs to filter by

    Returns:
        Filtered list of records
    """
    filtered = records

    for field, value in filters.items():
        if value is None:
            continue

        # Handle min/max filters
        if field.startswith("min_"):
            actual_field = field[4:]
            filtered = [r for r in filtered if r.get(actual_field, 0) >= value]
        elif field.startswith("max_"):
            actual_field = field[4:]
            filtered = [r for r in filtered if r.get(actual_field, float('inf')) <= value]
        # Handle list membership
        elif isinstance(value, list):
            filtered = [r for r in filtered if r.get(field) in value]
        # Handle exact match
        else:
            filtered = [r for r in filtered if r.get(field) == value]

    return filtered


def create_error_response(error_message: str, latency_ms: int = 0) -> MockResponse:
    """
    Create a standardized error response.

    Args:
        error_message: Description of the error
        latency_ms: Simulated latency

    Returns:
        MockResponse with error
    """
    return MockResponse(
        success=False,
        data=None,
        error=error_message,
        latency_ms=latency_ms
    )


def create_success_response(data: Any, latency_ms: int = 0) -> MockResponse:
    """
    Create a standardized success response.

    Args:
        data: Response data
        latency_ms: Simulated latency

    Returns:
        MockResponse with data
    """
    return MockResponse(
        success=True,
        data=data,
        error=None,
        latency_ms=latency_ms
    )
