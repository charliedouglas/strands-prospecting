"""Configuration settings for the prospecting agent."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AWS
    aws_region: str = "eu-west-2"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None

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
        """Pydantic config.

        AWS credentials are optional. If not provided via environment variables,
        the AWS SDK will use the default credential chain:
        1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        2. Shared credentials file (~/.aws/credentials)
        3. IAM role (if running on EC2/ECS/Lambda)

        To use explicit credentials, set:
        - AWS_ACCESS_KEY_ID
        - AWS_SECRET_ACCESS_KEY
        - AWS_SESSION_TOKEN (optional, for temporary credentials)
        """

        env_file = ".env"
        env_file_encoding = "utf-8"
