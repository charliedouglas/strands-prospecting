"""Configuration settings for the prospecting agent."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AWS
    aws_region: str = "eu-west-2"

    # Models (using cross-region inference profiles)
    planner_model: str = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
    executor_model: str = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
    reporter_model: str = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"

    # Extended thinking
    enable_extended_thinking: bool = True
    thinking_budget_tokens: int = 10000

    # Tool settings
    mock_apis: bool = True  # Use mock responses instead of real APIs
    api_timeout_seconds: int = 30
    max_retries: int = 2

    # Rate limits (per source)
    orbis_max_concurrent: int = 3

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
