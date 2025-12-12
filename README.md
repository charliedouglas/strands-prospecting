# Prospecting Agent

An agentic prospecting tool built on AWS Strands SDK that intelligently queries multiple data sources to gather comprehensive prospect information.

## Overview

The Prospecting Agent accepts natural language queries, plans optimal data source queries, executes them via mocked API calls, evaluates result sufficiency, and returns formatted reports.

### Key Features

- **Natural Language Queries**: Ask questions in plain English about companies, individuals, funding rounds, etc.
- **Multi-Source Intelligence**: Integrates data from Orbis, Wealth-X, Crunchbase, PitchBook, Companies House, and more
- **Intelligent Planning**: Uses Claude Sonnet 4.5 with extended thinking to create optimal query plans
- **Automated Execution**: Haiku 4.5 efficiently executes queries in parallel where possible
- **Quality Assurance**: Validates results for sufficiency and consistency before reporting

## Architecture

```
User Query → Planner Agent → Executor Agent → Sufficiency Checker → Report Generator
```

- **Planner Agent**: Analyzes queries and creates structured execution plans (Sonnet 4.5)
- **Executor Agent**: Executes plan steps and aggregates results (Haiku 4.5)
- **Sufficiency Checker**: Evaluates if results answer the original query (Sonnet 4.5)
- **Report Generator**: Creates formatted markdown reports (Sonnet 4.5)

## Technology Stack

- **Framework**: AWS Strands Agents SDK
- **Language**: Python 3.11+
- **Models**: Claude Sonnet 4.5 & Haiku 4.5 via AWS Bedrock
- **Infrastructure**: AWS Bedrock

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd prospecting-agent
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
```

4. Install development dependencies (optional):
```bash
pip install -e ".[dev]"
```

5. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your AWS credentials and preferences
```

## Configuration

Configuration is managed through environment variables (see `.env.example`) or can be set directly:

- `AWS_REGION`: AWS region for Bedrock (default: eu-west-2)
- `MOCK_APIS`: Use mock data sources (default: true)
- `ENABLE_EXTENDED_THINKING`: Enable extended thinking for planning (default: true)

See [src/config.py](src/config.py) for all configuration options.

## Usage

Run the agent:
```bash
python -m src.main
```

## Data Sources

The agent integrates with the following data sources (currently mocked):

- **Orbis**: Corporate structures, financials, ownership, directors
- **Wealth-X**: UHNW profiles, wealth composition, interests
- **Wealth Monitor**: UK-specific wealth data, property holdings
- **Companies House**: UK company filings, PSCs, directorships
- **Dun & Bradstreet**: Credit risk, business signals
- **Crunchbase**: Funding rounds, startup ecosystem
- **PitchBook**: PE/VC deals, private valuations
- **SerpAPI**: News search, recent events
- **Internal CRM**: Existing client checks

## Development

### Running Tests

```bash
pytest
```

### Code Quality

Format and lint code:
```bash
ruff check .
ruff format .
```

Type checking:
```bash
mypy src/
```

## Project Structure

```
prospecting-agent/
├── src/
│   ├── agents/          # Agent implementations
│   ├── models/          # Pydantic data models
│   ├── tools/           # Data source tools
│   ├── mocks/           # Mock API responses
│   ├── config.py        # Configuration
│   └── main.py          # Entry point
├── tests/               # Test suite
├── pyproject.toml       # Project metadata
└── README.md            # This file
```

## Example Queries

```
"Find UK tech companies that raised Series B in the last 12 months"

"Find UHNWIs in London with tech sector wealth over £50m interested in philanthropy"

"Get everything on ACME Technologies - ownership, financials, directors, recent news"
```

## Documentation

See [CLAUDE.md](CLAUDE.md) for comprehensive technical documentation including:
- Detailed architecture diagrams
- Data model specifications
- API structures for all data sources
- System prompts for agents
- Testing scenarios

## License

MIT
