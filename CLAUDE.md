# Prospecting Agent - Foundation Document

## Project Overview

An agentic prospecting tool built on AWS Strands SDK that:
1. Accepts natural language prospecting queries
2. Plans which data sources to query (using a reasoning model)
3. Executes the plan via mocked API calls
4. Evaluates result sufficiency
5. Returns a formatted report or requests clarification

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER QUERY                                   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PLANNER AGENT                                     │
│                    (Sonnet 4.5 + Extended Thinking)                  │
│                                                                      │
│  - Parses query intent                                               │
│  - Identifies required data sources                                  │
│  - Creates structured execution plan                                 │
│  - May request clarification if query ambiguous                      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ ExecutionPlan
┌─────────────────────────────────────────────────────────────────────┐
│                    EXECUTOR AGENT                                    │
│                    (Haiku 4.5)                                       │
│                                                                      │
│  - Follows plan sequentially                                         │
│  - Calls data source tools                                           │
│  - Aggregates results                                                │
│  - Handles errors/retries                                            │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ AggregatedResults
┌─────────────────────────────────────────────────────────────────────┐
│                    SUFFICIENCY CHECKER                               │
│                    (Sonnet 4.5 + Extended Thinking)                  │
│                                                                      │
│  - Evaluates if results answer original query                        │
│  - Identifies gaps                                                   │
│  - Returns: SUFFICIENT | CLARIFICATION_NEEDED | RETRY_NEEDED         │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              [SUFFICIENT]  [CLARIFY]      [RETRY]
                    │             │             │
                    ▼             ▼             │
┌──────────────────────┐  ┌─────────────┐      │
│   REPORT GENERATOR   │  │  Return to  │      │
│   (Sonnet 4.5)       │  │    User     │◄─────┘
└──────────────────────┘  └─────────────┘
                    │
                    ▼
            [Markdown Report]
```

## Technology Stack

- **Framework**: AWS Strands Agents SDK (`strands-agents`)
- **Language**: Python 3.11+
- **Models**: 
  - Planner/Sufficiency: Claude Sonnet 4.5 via Bedrock (with extended thinking)
  - Executor: Claude Haiku 4.5 via Bedrock
- **Infrastructure**: AWS Bedrock

## Directory Structure

```
prospecting-agent/
├── CLAUDE.md                    # This file
├── README.md
├── pyproject.toml
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── main.py                  # Entry point
│   ├── config.py                # Configuration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── plan.py              # ExecutionPlan, PlanStep
│   │   ├── results.py           # SearchResult, AggregatedResults
│   │   └── prospect.py          # ProspectProfile, Company, Individual
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── planner.py           # Planner agent
│   │   ├── executor.py          # Executor agent
│   │   ├── sufficiency.py       # Sufficiency checker
│   │   └── reporter.py          # Report generator
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py              # Base tool class
│   │   ├── orbis.py             # Bureau van Dijk Orbis
│   │   ├── wealthx.py           # Wealth-X
│   │   ├── wealth_monitor.py    # Wealth Monitor
│   │   ├── companies_house.py   # UK Companies House
│   │   ├── dun_bradstreet.py    # D&B Direct+
│   │   ├── crunchbase.py        # Crunchbase
│   │   ├── pitchbook.py         # PitchBook
│   │   ├── serpapi.py           # SerpAPI (news)
│   │   └── internal_crm.py      # Internal CRM
│   └── mocks/
│       ├── __init__.py
│       └── data/                # Mock response JSON files
│           ├── orbis/
│           ├── wealthx/
│           ├── companies_house/
│           ├── crunchbase/
│           ├── pitchbook/
│           ├── serpapi/
│           └── dun_bradstreet/
└── tests/
    ├── __init__.py
    ├── test_planner.py
    ├── test_executor.py
    ├── test_tools/
    └── test_e2e/
```

---

## Data Models

### ExecutionPlan

```python
from pydantic import BaseModel
from typing import Optional
from enum import Enum

class DataSource(str, Enum):
    ORBIS = "orbis"
    WEALTHX = "wealthx"
    WEALTH_MONITOR = "wealth_monitor"
    COMPANIES_HOUSE = "companies_house"
    DUN_BRADSTREET = "dun_bradstreet"
    CRUNCHBASE = "crunchbase"
    PITCHBOOK = "pitchbook"
    SERPAPI = "serpapi"
    INTERNAL_CRM = "internal_crm"

class PlanStep(BaseModel):
    step_id: int
    source: DataSource
    action: str                          # e.g., "search_funding", "get_directors"
    params: dict                         # Source-specific parameters
    reason: str                          # Why this step is needed
    depends_on: list[int] = []           # Step IDs this depends on
    
class ClarificationRequest(BaseModel):
    question: str
    options: list[str] | None = None     # Optional multiple choice
    context: str                         # Why clarification is needed

class ExecutionPlan(BaseModel):
    reasoning: str                       # Chain of thought from planner
    steps: list[PlanStep]
    clarification_needed: ClarificationRequest | None = None
    estimated_sources: int               # Number of unique sources
    confidence: float                    # 0-1, planner's confidence in plan
```

### SearchResult & AggregatedResults

```python
from pydantic import BaseModel
from datetime import datetime

class SearchResult(BaseModel):
    step_id: int
    source: DataSource
    success: bool
    data: dict | list | None             # Raw response data
    error: str | None = None
    record_count: int = 0
    execution_time_ms: int
    timestamp: datetime

class AggregatedResults(BaseModel):
    original_query: str
    plan: ExecutionPlan
    results: list[SearchResult]
    companies: list["Company"]           # Deduplicated companies found
    individuals: list["Individual"]      # Deduplicated individuals found
    total_records: int
    sources_queried: list[DataSource]
    execution_time_ms: int
```

### Prospect Entities

```python
class Company(BaseModel):
    # Identifiers
    id: str                              # Internal ID
    name: str
    bvd_id: str | None = None            # Orbis ID
    duns_number: str | None = None       # D&B DUNS
    companies_house_number: str | None = None
    crunchbase_uuid: str | None = None
    pitchbook_id: str | None = None
    
    # Basic info
    trading_names: list[str] = []
    country: str
    region: str | None = None
    city: str | None = None
    address: str | None = None
    website: str | None = None
    
    # Classification
    industry: str | None = None
    sic_codes: list[str] = []
    company_type: str | None = None      # e.g., "Private Limited"
    status: str | None = None            # e.g., "Active"
    
    # Financials
    revenue: float | None = None
    revenue_currency: str = "GBP"
    employee_count: int | None = None
    incorporation_date: str | None = None
    
    # Funding (from Crunchbase/PitchBook)
    total_funding: float | None = None
    funding_currency: str = "USD"
    last_funding_round: str | None = None
    last_funding_date: str | None = None
    last_funding_amount: float | None = None
    investors: list[str] = []
    
    # Ownership
    ultimate_parent: str | None = None
    immediate_parent: str | None = None
    
    # Metadata
    sources: list[DataSource] = []
    last_updated: datetime | None = None

class Individual(BaseModel):
    # Identifiers
    id: str
    name: str
    wealthx_id: str | None = None
    orbis_contact_id: str | None = None
    
    # Basic info
    title: str | None = None             # e.g., "Mr", "Dr"
    first_name: str | None = None
    last_name: str | None = None
    gender: str | None = None
    nationality: str | None = None
    country_of_residence: str | None = None
    city: str | None = None
    
    # Professional
    current_roles: list["Role"] = []
    previous_roles: list["Role"] = []
    
    # Wealth (from Wealth-X/Wealth Monitor)
    net_worth: float | None = None
    net_worth_currency: str = "USD"
    wealth_source: str | None = None     # e.g., "Inherited", "Self-made"
    liquidity: float | None = None
    
    # Interests/passions (from Wealth-X)
    interests: list[str] = []
    philanthropy: list[str] = []
    
    # Connections
    known_associates: list[str] = []
    
    # Metadata
    sources: list[DataSource] = []
    is_existing_client: bool = False
    last_updated: datetime | None = None

class Role(BaseModel):
    company_name: str
    company_id: str | None = None
    title: str
    role_type: str | None = None         # e.g., "Director", "PSC", "Founder"
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = True
```

---

## Data Source Specifications

### 1. Orbis (Bureau van Dijk)

**Purpose**: Corporate structures, financials, ownership, directors

**Mock API Structure**:
```python
# Search companies
POST /api/v1/companies/search
{
    "query": {
        "name": "string",
        "country": "string",          # ISO 2-letter
        "region": "string",
        "city": "string",
        "bvd_id": "string",
        "national_id": "string",      # e.g., Companies House number
        "status": ["Active", "Inactive"],
        "industry_codes": ["string"],
        "min_revenue": float,
        "max_revenue": float,
        "min_employees": int,
        "max_employees": int
    },
    "limit": 100,
    "offset": 0
}

# Response
{
    "total_count": 150,
    "results": [
        {
            "bvd_id": "GB12345678",
            "name": "ACME TECHNOLOGIES LTD",
            "country": "GB",
            "status": "Active",
            "incorporation_date": "2015-03-21",
            "company_type": "Private limited with share capital",
            "registered_address": {
                "line1": "123 Tech Park",
                "city": "London",
                "postcode": "EC1A 1BB",
                "country": "GB"
            },
            "operating_revenue": 15000000,
            "operating_revenue_currency": "GBP",
            "employees": 85,
            "industry": {
                "primary_code": "62020",
                "primary_description": "Information technology consultancy"
            },
            "national_ids": [
                {"type": "Companies House", "value": "12345678"}
            ]
        }
    ]
}

# Get company directors
GET /api/v1/companies/{bvd_id}/directors

# Response
{
    "bvd_id": "GB12345678",
    "company_name": "ACME TECHNOLOGIES LTD",
    "directors": [
        {
            "contact_id": "P123456",
            "name": "John Smith",
            "title": "Mr",
            "role": "Director",
            "appointment_date": "2015-03-21",
            "resignation_date": null,
            "is_current": true,
            "nationality": "British",
            "date_of_birth": "1975-06"
        }
    ]
}

# Get ownership structure
GET /api/v1/companies/{bvd_id}/ownership

# Response
{
    "bvd_id": "GB12345678",
    "company_name": "ACME TECHNOLOGIES LTD",
    "shareholders": [
        {
            "name": "John Smith",
            "type": "Individual",
            "percentage": 60.0,
            "is_direct": true
        },
        {
            "name": "Tech Holdings Ltd",
            "type": "Corporate",
            "bvd_id": "GB87654321",
            "percentage": 40.0,
            "is_direct": true
        }
    ],
    "ultimate_owner": {
        "name": "John Smith",
        "type": "Individual",
        "percentage": 60.0
    }
}
```

### 2. Crunchbase

**Purpose**: Funding rounds, startup ecosystem, investors

**Mock API Structure** (based on Crunchbase API v4):
```python
# Search funding rounds
POST /v4/data/searches/funding_rounds
{
    "field_ids": [
        "identifier",
        "announced_on",
        "funded_organization_identifier",
        "money_raised",
        "investment_type",
        "investor_identifiers",
        "lead_investor_identifiers"
    ],
    "query": [
        {
            "type": "predicate",
            "field_id": "investment_type",
            "operator_id": "eq",
            "values": ["series_b"]
        },
        {
            "type": "predicate",
            "field_id": "funded_organization_location_identifiers",
            "operator_id": "includes",
            "values": ["united-kingdom"]
        },
        {
            "type": "predicate",
            "field_id": "announced_on",
            "operator_id": "gte",
            "values": ["2023-01-01"]
        }
    ],
    "order": [
        {"field_id": "announced_on", "sort": "desc"}
    ],
    "limit": 50
}

# Response
{
    "count": 45,
    "entities": [
        {
            "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "properties": {
                "identifier": {
                    "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "value": "series-b--acme-technologies",
                    "permalink": "series-b--acme-technologies"
                },
                "announced_on": "2024-06-15",
                "money_raised": {
                    "value": 25000000,
                    "currency": "GBP",
                    "value_usd": 31500000
                },
                "investment_type": "series_b",
                "funded_organization_identifier": {
                    "uuid": "org-uuid-12345",
                    "value": "ACME Technologies",
                    "permalink": "acme-technologies"
                },
                "investor_identifiers": [
                    {"value": "Sequoia Capital", "permalink": "sequoia-capital"},
                    {"value": "Index Ventures", "permalink": "index-ventures"}
                ],
                "lead_investor_identifiers": [
                    {"value": "Sequoia Capital", "permalink": "sequoia-capital"}
                ]
            }
        }
    ]
}

# Get organization details
GET /v4/data/entities/organizations/{permalink}
{
    "field_ids": [
        "identifier", "short_description", "founded_on",
        "num_employees_enum", "website", "linkedin",
        "location_identifiers", "categories", "funding_total"
    ]
}

# Response
{
    "properties": {
        "identifier": {
            "uuid": "org-uuid-12345",
            "value": "ACME Technologies",
            "permalink": "acme-technologies"
        },
        "short_description": "Enterprise AI platform for financial services",
        "founded_on": "2018-03-15",
        "num_employees_enum": "c_00051_00100",
        "website": {"value": "https://acmetech.io"},
        "linkedin": {"value": "https://linkedin.com/company/acmetech"},
        "location_identifiers": [
            {"value": "London", "location_type": "city"},
            {"value": "United Kingdom", "location_type": "country"}
        ],
        "categories": [
            {"value": "Artificial Intelligence"},
            {"value": "Financial Services"},
            {"value": "SaaS"}
        ],
        "funding_total": {
            "value": 42000000,
            "currency": "GBP",
            "value_usd": 52920000
        }
    }
}
```

### 3. PitchBook

**Purpose**: PE/VC deals, private valuations, investor networks

**Mock API Structure**:
```python
# Search deals
POST /v2/deals/search
{
    "filters": {
        "deal_type": ["VC", "PE Growth"],
        "deal_status": ["Completed"],
        "regions": ["Europe"],
        "countries": ["United Kingdom"],
        "industries": ["Information Technology"],
        "deal_size_min": 10000000,
        "deal_size_max": 100000000,
        "deal_date_min": "2023-01-01",
        "series": ["B", "C"]
    },
    "sort": {"field": "deal_date", "order": "desc"},
    "limit": 50,
    "offset": 0
}

# Response
{
    "total_count": 127,
    "deals": [
        {
            "deal_id": "PB-DEAL-123456",
            "deal_date": "2024-06-15",
            "deal_type": "VC",
            "deal_status": "Completed",
            "series": "Series B",
            "deal_size": 25000000,
            "deal_size_currency": "GBP",
            "pre_money_valuation": 75000000,
            "post_money_valuation": 100000000,
            "company": {
                "company_id": "PB-CO-789012",
                "name": "ACME Technologies",
                "primary_industry": "Application Software",
                "hq_location": "London, United Kingdom",
                "website": "https://acmetech.io",
                "founded_year": 2018,
                "employee_count": 85
            },
            "investors": [
                {
                    "investor_id": "PB-INV-111",
                    "name": "Sequoia Capital",
                    "investor_type": "Venture Capital",
                    "is_lead": true
                },
                {
                    "investor_id": "PB-INV-222",
                    "name": "Index Ventures",
                    "investor_type": "Venture Capital",
                    "is_lead": false
                }
            ]
        }
    ]
}

# Get company profile
GET /v2/companies/{company_id}

# Response
{
    "company_id": "PB-CO-789012",
    "name": "ACME Technologies",
    "description": "Enterprise AI platform for financial services",
    "primary_industry": "Application Software",
    "primary_sector": "Information Technology",
    "hq_location": {
        "city": "London",
        "country": "United Kingdom"
    },
    "website": "https://acmetech.io",
    "founded_year": 2018,
    "employee_count": 85,
    "ownership_status": "Privately Held",
    "financing_status": "Venture Capital-Backed",
    "total_raised": 42000000,
    "total_raised_currency": "GBP",
    "last_financing_date": "2024-06-15",
    "last_financing_size": 25000000,
    "last_financing_type": "Series B",
    "post_money_valuation": 100000000,
    "executives": [
        {
            "person_id": "PB-PER-001",
            "name": "John Smith",
            "title": "Chief Executive Officer",
            "start_date": "2018-03-15"
        },
        {
            "person_id": "PB-PER-002",
            "name": "Jane Doe",
            "title": "Chief Technology Officer",
            "start_date": "2019-01-10"
        }
    ]
}
```

### 4. Companies House (UK)

**Purpose**: UK company filings, PSCs, directorships

**Mock API Structure** (based on actual Companies House API):
```python
# Search companies
GET /search/companies?q={query}

# Response
{
    "items_per_page": 20,
    "kind": "search#companies",
    "start_index": 0,
    "total_results": 5,
    "items": [
        {
            "company_number": "12345678",
            "company_status": "active",
            "company_type": "ltd",
            "title": "ACME TECHNOLOGIES LTD",
            "date_of_creation": "2018-03-15",
            "address": {
                "address_line_1": "123 Tech Park",
                "locality": "London",
                "postal_code": "EC1A 1BB",
                "country": "United Kingdom"
            },
            "description": "12345678 - Incorporated on 15 March 2018",
            "snippet": "Information technology consultancy activities"
        }
    ]
}

# Get company profile
GET /company/{company_number}

# Response
{
    "company_number": "12345678",
    "company_name": "ACME TECHNOLOGIES LTD",
    "type": "ltd",
    "company_status": "active",
    "date_of_creation": "2018-03-15",
    "jurisdiction": "england-wales",
    "registered_office_address": {
        "address_line_1": "123 Tech Park",
        "address_line_2": "Innovation Quarter",
        "locality": "London",
        "postal_code": "EC1A 1BB",
        "country": "United Kingdom"
    },
    "sic_codes": ["62020"],
    "accounts": {
        "accounting_reference_date": {"day": 31, "month": 3},
        "last_accounts": {
            "made_up_to": "2024-03-31",
            "type": "full"
        },
        "next_due": "2025-12-31",
        "next_made_up_to": "2025-03-31"
    },
    "confirmation_statement": {
        "last_made_up_to": "2024-03-14",
        "next_due": "2025-03-28",
        "next_made_up_to": "2025-03-14"
    },
    "links": {
        "officers": "/company/12345678/officers",
        "persons_with_significant_control": "/company/12345678/persons-with-significant-control",
        "filing_history": "/company/12345678/filing-history"
    }
}

# Get officers
GET /company/{company_number}/officers

# Response
{
    "items_per_page": 35,
    "kind": "officer-list",
    "start_index": 0,
    "total_results": 3,
    "items": [
        {
            "name": "SMITH, John David",
            "officer_role": "director",
            "appointed_on": "2018-03-15",
            "date_of_birth": {"month": 6, "year": 1975},
            "nationality": "British",
            "country_of_residence": "United Kingdom",
            "occupation": "Company Director",
            "address": {
                "address_line_1": "123 Tech Park",
                "locality": "London",
                "postal_code": "EC1A 1BB"
            },
            "links": {
                "officer": {
                    "appointments": "/officers/ABC123DEF456/appointments"
                }
            }
        }
    ]
}

# Get PSCs (Persons with Significant Control)
GET /company/{company_number}/persons-with-significant-control

# Response
{
    "items_per_page": 25,
    "kind": "persons-with-significant-control#list",
    "start_index": 0,
    "total_results": 2,
    "items": [
        {
            "name": "Mr John David Smith",
            "name_elements": {
                "title": "Mr",
                "forename": "John",
                "other_forenames": "David",
                "surname": "Smith"
            },
            "nationality": "British",
            "country_of_residence": "United Kingdom",
            "date_of_birth": {"month": 6, "year": 1975},
            "notified_on": "2018-03-15",
            "natures_of_control": [
                "ownership-of-shares-50-to-75-percent",
                "voting-rights-50-to-75-percent"
            ],
            "kind": "individual-person-with-significant-control"
        }
    ]
}
```

### 5. Wealth-X

**Purpose**: UHNW profiles, wealth composition, interests, connections

**Mock API Structure**:
```python
# Search individuals
POST /api/v2/profiles/search
{
    "filters": {
        "net_worth_min": 30000000,
        "net_worth_max": null,
        "countries": ["GB", "US"],
        "industries": ["Technology", "Finance"],
        "interests": ["Philanthropy", "Art"],
        "keywords": "founder CEO tech"
    },
    "limit": 50,
    "offset": 0
}

# Response
{
    "total_count": 23,
    "profiles": [
        {
            "wealthx_id": "WX-123456",
            "name": "John David Smith",
            "title": "Mr",
            "first_name": "John",
            "middle_name": "David",
            "last_name": "Smith",
            "gender": "Male",
            "age": 49,
            "nationality": "British",
            "country_of_residence": "United Kingdom",
            "city": "London",
            "net_worth": {
                "value": 85000000,
                "currency": "USD",
                "confidence": "High",
                "last_updated": "2024-03-15"
            },
            "wealth_source": "Self-made",
            "primary_industry": "Technology",
            "liquidity": {
                "value": 25000000,
                "currency": "USD"
            },
            "assets": {
                "public_holdings": 5000000,
                "private_holdings": 60000000,
                "real_estate": 15000000,
                "luxury_assets": 3000000,
                "cash": 2000000
            }
        }
    ]
}

# Get full profile
GET /api/v2/profiles/{wealthx_id}

# Response
{
    "wealthx_id": "WX-123456",
    "name": "John David Smith",
    "title": "Mr",
    "first_name": "John",
    "middle_name": "David",
    "last_name": "Smith",
    "gender": "Male",
    "date_of_birth": "1975-06-15",
    "age": 49,
    "nationality": "British",
    "country_of_residence": "United Kingdom",
    "city": "London",
    "education": [
        {
            "institution": "University of Oxford",
            "degree": "MBA",
            "year": 2002
        }
    ],
    "net_worth": {
        "value": 85000000,
        "currency": "USD",
        "confidence": "High",
        "last_updated": "2024-03-15"
    },
    "wealth_source": "Self-made",
    "primary_industry": "Technology",
    "biography": "John Smith is a technology entrepreneur and founder of ACME Technologies...",
    "current_positions": [
        {
            "company": "ACME Technologies Ltd",
            "title": "Founder & CEO",
            "start_year": 2018
        }
    ],
    "previous_positions": [
        {
            "company": "BigTech Corp",
            "title": "VP Engineering",
            "start_year": 2010,
            "end_year": 2017
        }
    ],
    "board_memberships": [
        {
            "organization": "Tech for Good Foundation",
            "role": "Trustee",
            "type": "Non-profit"
        }
    ],
    "interests": ["Technology", "Sustainable investing", "Classical music"],
    "philanthropy": {
        "causes": ["Education", "Climate change"],
        "estimated_annual_giving": 500000,
        "notable_donations": [
            {"recipient": "Oxford University", "amount": 1000000, "year": 2023}
        ]
    },
    "known_associates": [
        {
            "name": "Jane Doe",
            "relationship": "Business partner",
            "wealthx_id": "WX-789012"
        }
    ],
    "lifestyle": {
        "primary_residence": "London, UK",
        "secondary_residences": ["Monaco"],
        "luxury_assets": ["Yacht", "Art collection"]
    }
}
```

### 6. Dun & Bradstreet (D&B Direct+)

**Purpose**: Credit risk, business signals, firmographics

**Mock API Structure** (based on D&B Direct+ API):
```python
# Match and enrich company
POST /v1/match/cleanseMatch
{
    "duns": null,
    "name": "ACME Technologies",
    "countryISOAlpha2Code": "GB",
    "addressLocality": "London"
}

# Response
{
    "matchCandidates": [
        {
            "organization": {
                "duns": "123456789",
                "primaryName": "ACME TECHNOLOGIES LTD",
                "dunsControlStatus": {
                    "operatingStatus": {"description": "Active"}
                },
                "primaryAddress": {
                    "addressLocality": {"name": "London"},
                    "addressRegion": {"name": "Greater London"},
                    "addressCountry": {"isoAlpha2Code": "GB"},
                    "postalCode": "EC1A 1BB"
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

# Get company data blocks
GET /v1/data/duns/{duns_number}?blockIDs=companyinfo_L2,principalscontacts_L1,hierarchyconnections_L1

# Response
{
    "organization": {
        "duns": "123456789",
        "primaryName": "ACME TECHNOLOGIES LTD",
        "tradeStyleNames": [{"name": "ACME Tech"}],
        "telephone": [{"telephoneNumber": "+44 20 1234 5678"}],
        "websiteAddress": [{"url": "https://acmetech.io"}],
        "dunsControlStatus": {
            "operatingStatus": {"description": "Active"},
            "operatingSubStatus": {"description": "Operating"}
        },
        "startDate": "2018-03-15",
        "incorporatedDate": "2018-03-15",
        "legalForm": {"description": "Private Limited Company"},
        "registrationNumbers": [
            {
                "registrationNumber": "12345678",
                "typeDnBCode": 1354,
                "typeDescription": "UK Company Registration Number"
            }
        ],
        "industryCodes": [
            {
                "code": "62020",
                "description": "Information technology consultancy activities",
                "typeDescription": "UK SIC 2007"
            }
        ],
        "primaryAddress": {
            "streetAddress": {"line1": "123 Tech Park"},
            "addressLocality": {"name": "London"},
            "addressRegion": {"name": "Greater London"},
            "postalCode": "EC1A 1BB",
            "addressCountry": {"isoAlpha2Code": "GB"}
        },
        "numberOfEmployees": [
            {
                "value": 85,
                "informationScopeDescription": "Individual",
                "reliabilityDescription": "Actual"
            }
        ],
        "financials": [
            {
                "yearlyRevenue": [
                    {
                        "value": 15000000,
                        "currency": "GBP",
                        "reliabilityDescription": "Actual"
                    }
                ],
                "financialStatementToDate": "2024-03-31"
            }
        ],
        "dnbAssessment": {
            "failureScore": {
                "nationalPercentile": 15,
                "scoreCommentary": "Low risk"
            },
            "delinquencyScore": {
                "nationalPercentile": 12,
                "scoreCommentary": "Low risk"
            }
        }
    },
    "principals": [
        {
            "fullName": "John David Smith",
            "namePrefix": "Mr",
            "givenName": "John",
            "middleName": "David", 
            "familyName": "Smith",
            "jobTitles": [{"title": "Director"}],
            "managementResponsibilities": [
                {"description": "Chief Executive Officer"}
            ]
        }
    ],
    "corporateLinkage": {
        "globalUltimate": {
            "duns": "123456789",
            "primaryName": "ACME TECHNOLOGIES LTD"
        },
        "domesticUltimate": {
            "duns": "123456789",
            "primaryName": "ACME TECHNOLOGIES LTD"
        },
        "familyTreeMembersCount": 1
    }
}
```

### 7. SerpAPI (News Search)

**Purpose**: News signals, recent events, early funding announcements

**Mock API Structure** (based on SerpAPI):
```python
# Search news
GET /search?engine=google_news&q={query}&api_key={key}

# Response
{
    "search_metadata": {
        "id": "search-id-123",
        "status": "Success",
        "created_at": "2024-12-12 10:30:00 UTC",
        "processed_at": "2024-12-12 10:30:01 UTC",
        "total_time_taken": 0.8
    },
    "search_parameters": {
        "engine": "google_news",
        "q": "ACME Technologies funding",
        "gl": "uk"
    },
    "news_results": [
        {
            "position": 1,
            "title": "ACME Technologies raises £25M Series B to expand AI platform",
            "link": "https://techcrunch.com/2024/06/15/acme-technologies-series-b/",
            "source": {
                "name": "TechCrunch",
                "icon": "https://techcrunch.com/favicon.ico"
            },
            "date": "2 days ago",
            "snippet": "London-based ACME Technologies has raised £25 million in Series B funding led by Sequoia Capital to expand its enterprise AI platform...",
            "thumbnail": "https://example.com/image.jpg"
        },
        {
            "position": 2,
            "title": "UK fintech sector sees record investment in H1 2024",
            "link": "https://ft.com/content/abc123",
            "source": {
                "name": "Financial Times",
                "icon": "https://ft.com/favicon.ico"
            },
            "date": "1 week ago",
            "snippet": "British fintech companies attracted £4.2bn in venture capital during the first half of 2024, with notable rounds including ACME Technologies..."
        }
    ],
    "pagination": {
        "current": 1,
        "next": "https://serpapi.com/search?...&start=10"
    }
}

# General web search (for broader queries)
GET /search?engine=google&q={query}&api_key={key}

# Response
{
    "search_metadata": {
        "id": "search-id-456",
        "status": "Success"
    },
    "organic_results": [
        {
            "position": 1,
            "title": "ACME Technologies | Enterprise AI Platform",
            "link": "https://acmetech.io",
            "displayed_link": "https://acmetech.io",
            "snippet": "ACME Technologies provides enterprise-grade AI solutions for financial services...",
            "sitelinks": {
                "inline": [
                    {"title": "About", "link": "https://acmetech.io/about"},
                    {"title": "Careers", "link": "https://acmetech.io/careers"}
                ]
            }
        }
    ],
    "knowledge_graph": {
        "title": "ACME Technologies",
        "type": "Technology company",
        "description": "British artificial intelligence company founded in 2018",
        "founded": "2018",
        "headquarters": "London, United Kingdom"
    }
}
```

### 8. Wealth Monitor (UK)

**Purpose**: UK-specific wealth data, property, shareholdings

**Mock API Structure**:
```python
# Search individuals
POST /api/v1/individuals/search
{
    "name": "John Smith",
    "region": "London",
    "min_net_worth": 10000000,
    "include_property": true,
    "include_shareholdings": true
}

# Response
{
    "total_count": 3,
    "individuals": [
        {
            "wm_id": "WM-UK-123456",
            "name": "John David Smith",
            "estimated_net_worth": 85000000,
            "estimated_net_worth_gbp": 68000000,
            "confidence": "High",
            "region": "London",
            "property_portfolio": {
                "total_value": 12000000,
                "properties": [
                    {
                        "address": "Flat 10, Kensington Gardens",
                        "city": "London",
                        "postcode": "W8 4PX",
                        "estimated_value": 8500000,
                        "ownership_type": "Freehold",
                        "acquired_date": "2019-05-15"
                    },
                    {
                        "address": "The Manor House",
                        "city": "Oxfordshire",
                        "postcode": "OX7 5QG",
                        "estimated_value": 3500000,
                        "ownership_type": "Freehold"
                    }
                ]
            },
            "shareholdings": {
                "total_value": 45000000,
                "holdings": [
                    {
                        "company_name": "ACME Technologies Ltd",
                        "company_number": "12345678",
                        "shares_held": 6000000,
                        "percentage": 60.0,
                        "estimated_value": 42000000
                    }
                ]
            },
            "directorships": [
                {
                    "company_name": "ACME Technologies Ltd",
                    "company_number": "12345678",
                    "role": "Director",
                    "appointed": "2018-03-15",
                    "status": "Active"
                }
            ]
        }
    ]
}
```

### 9. Internal CRM

**Purpose**: Existing client check, relationship history, exclusions

**Mock API Structure**:
```python
# Check if individual is existing client
POST /api/v1/clients/check
{
    "individuals": [
        {"name": "John Smith", "company": "ACME Technologies"},
        {"name": "Jane Doe", "company": "TechCorp"}
    ],
    "companies": [
        {"name": "ACME Technologies", "company_number": "12345678"}
    ]
}

# Response
{
    "matches": {
        "individuals": [
            {
                "query_name": "John Smith",
                "is_client": false,
                "is_prospect": true,
                "is_excluded": false,
                "relationship_manager": null,
                "notes": "Prospect - initial meeting scheduled"
            },
            {
                "query_name": "Jane Doe",
                "is_client": true,
                "is_prospect": false,
                "is_excluded": false,
                "client_id": "CL-789012",
                "relationship_manager": "Sarah Johnson",
                "client_since": "2020-06-15",
                "aum": 15000000,
                "last_contact": "2024-11-20"
            }
        ],
        "companies": [
            {
                "query_name": "ACME Technologies",
                "is_client": false,
                "is_prospect": true,
                "notes": "Corporate prospect via founder"
            }
        ]
    }
}

# Get exclusion list
GET /api/v1/exclusions

# Response
{
    "individuals": [
        {
            "name": "Bad Actor",
            "reason": "Compliance concern",
            "added_date": "2023-01-15"
        }
    ],
    "companies": [
        {
            "name": "Suspicious Corp",
            "company_number": "99999999",
            "reason": "AML flag",
            "added_date": "2022-08-20"
        }
    ]
}
```

---

## Data Source Selection Logic

The planner should use this logic when deciding which sources to query:

| Query Type | Primary Sources | Secondary Sources |
|------------|-----------------|-------------------|
| **Funding/Investment** | Crunchbase, PitchBook | SerpAPI (news), Orbis |
| **UHNW Individual** | Wealth-X, Wealth Monitor | Companies House (directorships) |
| **UK Company Structure** | Orbis, Companies House | D&B |
| **Directors/Founders** | Companies House, Orbis | Wealth-X, PitchBook |
| **Credit/Risk** | D&B | Orbis |
| **Recent News/Signals** | SerpAPI | - |
| **Client Exclusion** | Internal CRM | - |

**Always include Internal CRM** at the end of any prospect-focused query to filter existing clients.

---

## System Prompts

### Planner Agent System Prompt

```
You are a prospecting research planner for a private bank. Your job is to analyze prospecting queries and create structured execution plans.

Available data sources:
- ORBIS: Corporate structures, financials, ownership, directors (Bureau van Dijk)
- WEALTHX: UHNW individual profiles, wealth composition, interests, connections
- WEALTH_MONITOR: UK-specific wealth data, property, shareholdings
- COMPANIES_HOUSE: UK company filings, PSCs, directorships (free, authoritative)
- DUN_BRADSTREET: Credit risk, business signals, firmographics
- CRUNCHBASE: Funding rounds, startup ecosystem, investors
- PITCHBOOK: PE/VC deals, private valuations, investor networks
- SERPAPI: News search, recent events
- INTERNAL_CRM: Existing client check, exclusions

When creating a plan:
1. Parse the query to understand what information is needed
2. Identify which data sources can provide that information
3. Determine the optimal order (dependencies matter - e.g., find companies before looking up directors)
4. Consider cross-referencing for accuracy (e.g., both Crunchbase AND PitchBook for funding)
5. ALWAYS include INTERNAL_CRM as the final step to filter out existing clients

If the query is ambiguous or missing critical information, request clarification instead of guessing.

Output a structured ExecutionPlan with:
- reasoning: Your chain of thought
- steps: Ordered list of data source queries with specific parameters
- clarification_needed: Only if the query is too ambiguous to proceed
- confidence: Your confidence in this plan (0-1)
```

### Executor Agent System Prompt

```
You are a data retrieval agent. Your job is to execute a pre-defined plan by calling the appropriate data source tools in order.

Rules:
1. Follow the plan exactly - do not improvise or add steps
2. Execute steps in order, respecting dependencies
3. If a step fails, log the error and continue to the next step
4. Aggregate all results for the sufficiency checker

For each step:
1. Parse the step parameters
2. Call the appropriate tool
3. Record the result (success/failure, data, timing)

Do not analyze or filter the data - that's the sufficiency checker's job.
```

### Sufficiency Checker System Prompt

```
You are a quality assurance agent for prospecting research. Your job is to evaluate whether the gathered data adequately answers the original query.

Evaluate:
1. Does the data answer the original question?
2. Are there critical gaps? (e.g., asked for founders but only got company data)
3. Is the data internally consistent across sources?
4. Should any results be excluded (existing clients, compliance concerns)?

Return one of:
- SUFFICIENT: Data answers the query, proceed to report generation
- CLARIFICATION_NEEDED: Need user input to refine the search
- RETRY_NEEDED: Should re-run certain steps with modified parameters

Include reasoning for your decision.
```

---

## Configuration

```python
# src/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # AWS
    aws_region: str = "eu-west-2"
    
    # Models
    planner_model: str = "eu.anthropic.claude-sonnet-4-5-20250514-v1:0"
    executor_model: str = "eu.anthropic.claude-haiku-4-5-20250514-v1:0"
    reporter_model: str = "eu.anthropic.claude-sonnet-4-5-20250514-v1:0"
    
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
        env_file = ".env"
```

---

## Testing Scenarios

### Scenario 1: Funding-focused query
```
"Find UK tech companies that raised Series B in the last 12 months with female founders"
```
Expected plan:
1. Crunchbase → search funding rounds (series_b, UK, last 12 months)
2. PitchBook → cross-reference funding rounds
3. Companies House → get directors for matched companies
4. Wealth-X → enrich founder profiles (filter female)
5. Internal CRM → exclude existing clients

### Scenario 2: UHNW individual query
```
"Find UHNWIs in London with tech sector wealth over £50m who are interested in philanthropy"
```
Expected plan:
1. Wealth-X → search profiles (London, tech, >£50m, philanthropy interest)
2. Wealth Monitor → cross-reference UK wealth data
3. Companies House → get current directorships
4. Internal CRM → exclude existing clients

### Scenario 3: Company-focused query
```
"Get me everything on ACME Technologies - ownership, financials, directors, any recent news"
```
Expected plan:
1. Companies House → search company, get profile
2. Orbis → full company profile, ownership structure
3. D&B → credit assessment, firmographics
4. Crunchbase → funding history
5. PitchBook → valuation, investor info
6. SerpAPI → recent news
7. Wealth-X → director wealth profiles
8. Internal CRM → check relationship status

---

## Error Handling

```python
class ProspectingError(Exception):
    """Base exception for prospecting agent"""
    pass

class DataSourceError(ProspectingError):
    """Error from a specific data source"""
    def __init__(self, source: DataSource, message: str, retryable: bool = True):
        self.source = source
        self.retryable = retryable
        super().__init__(f"{source.value}: {message}")

class PlanningError(ProspectingError):
    """Error during plan creation"""
    pass

class InsufficientDataError(ProspectingError):
    """Not enough data to answer query"""
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"Missing data: {', '.join(missing)}")
```