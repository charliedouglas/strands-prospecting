"""
Prospect entity models for the prospecting agent.

This module defines data structures for companies, individuals, and their
relationships as discovered through various data sources.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

from .plan import DataSource


class Role(BaseModel):
    """
    A professional role held by an individual at a company.

    Represents current or past positions, including directorships,
    executive roles, and board memberships.
    """
    company_name: str = Field(..., description="Name of the company")
    company_id: Optional[str] = Field(None, description="Internal ID of the company if known")
    title: str = Field(..., description="Job title or role name")
    role_type: Optional[str] = Field(None, description="Type of role, e.g., 'Director', 'PSC', 'Founder', 'Executive'")
    start_date: Optional[str] = Field(None, description="Start date of the role (ISO format)")
    end_date: Optional[str] = Field(None, description="End date of the role (ISO format)")
    is_current: bool = Field(True, description="Whether this is a current role")

    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "ACME Technologies Ltd",
                "company_id": "GB12345678",
                "title": "Chief Executive Officer",
                "role_type": "Executive",
                "start_date": "2018-03-15",
                "end_date": None,
                "is_current": True
            }
        }


class Company(BaseModel):
    """
    A company prospect entity.

    Aggregates information from multiple data sources including identifiers,
    basic information, classification, financials, funding, and ownership.
    """
    # Identifiers
    id: str = Field(..., description="Internal unique identifier")
    name: str = Field(..., description="Primary company name")
    bvd_id: Optional[str] = Field(None, description="Bureau van Dijk (Orbis) ID")
    duns_number: Optional[str] = Field(None, description="Dun & Bradstreet DUNS number")
    companies_house_number: Optional[str] = Field(None, description="UK Companies House registration number")
    crunchbase_uuid: Optional[str] = Field(None, description="Crunchbase UUID")
    pitchbook_id: Optional[str] = Field(None, description="PitchBook company ID")

    # Basic info
    trading_names: list[str] = Field(default_factory=list, description="Alternative trading names")
    country: str = Field(..., description="Country of incorporation (ISO 2-letter code)")
    region: Optional[str] = Field(None, description="Region or state")
    city: Optional[str] = Field(None, description="City")
    address: Optional[str] = Field(None, description="Full registered address")
    website: Optional[str] = Field(None, description="Company website URL")

    # Classification
    industry: Optional[str] = Field(None, description="Primary industry")
    sic_codes: list[str] = Field(default_factory=list, description="Standard Industrial Classification codes")
    company_type: Optional[str] = Field(None, description="Legal form, e.g., 'Private Limited Company'")
    status: Optional[str] = Field(None, description="Company status, e.g., 'Active', 'Dissolved'")

    # Financials
    revenue: Optional[float] = Field(None, description="Annual revenue")
    revenue_currency: str = Field("GBP", description="Currency of revenue figure")
    employee_count: Optional[int] = Field(None, description="Number of employees")
    incorporation_date: Optional[str] = Field(None, description="Date of incorporation (ISO format)")

    # Funding (from Crunchbase/PitchBook)
    total_funding: Optional[float] = Field(None, description="Total funding raised")
    funding_currency: str = Field("USD", description="Currency of funding figures")
    last_funding_round: Optional[str] = Field(None, description="Type of last funding round, e.g., 'Series B'")
    last_funding_date: Optional[str] = Field(None, description="Date of last funding round (ISO format)")
    last_funding_amount: Optional[float] = Field(None, description="Amount raised in last funding round")
    investors: list[str] = Field(default_factory=list, description="List of investor names")

    # Ownership
    ultimate_parent: Optional[str] = Field(None, description="Ultimate parent company name")
    immediate_parent: Optional[str] = Field(None, description="Immediate parent company name")

    # Metadata
    sources: list[DataSource] = Field(default_factory=list, description="Data sources that provided information")
    last_updated: Optional[datetime] = Field(None, description="When this record was last updated")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "comp_001",
                "name": "ACME TECHNOLOGIES LTD",
                "bvd_id": "GB12345678",
                "duns_number": "123456789",
                "companies_house_number": "12345678",
                "crunchbase_uuid": "abc-123-def",
                "pitchbook_id": "PB-CO-789012",
                "trading_names": ["ACME Tech"],
                "country": "GB",
                "region": "Greater London",
                "city": "London",
                "address": "123 Tech Park, London, EC1A 1BB",
                "website": "https://acmetech.io",
                "industry": "Information Technology",
                "sic_codes": ["62020"],
                "company_type": "Private Limited Company",
                "status": "Active",
                "revenue": 15000000,
                "revenue_currency": "GBP",
                "employee_count": 85,
                "incorporation_date": "2018-03-15",
                "total_funding": 42000000,
                "funding_currency": "USD",
                "last_funding_round": "Series B",
                "last_funding_date": "2024-06-15",
                "last_funding_amount": 25000000,
                "investors": ["Sequoia Capital", "Index Ventures"],
                "ultimate_parent": None,
                "immediate_parent": None,
                "sources": ["crunchbase", "companies_house", "orbis"],
                "last_updated": "2024-12-12T10:30:00Z"
            }
        }


class Individual(BaseModel):
    """
    An individual prospect entity.

    Aggregates information from multiple data sources including identifiers,
    basic information, professional roles, wealth data, and connections.
    """
    # Identifiers
    id: str = Field(..., description="Internal unique identifier")
    name: str = Field(..., description="Full name")
    wealthx_id: Optional[str] = Field(None, description="Wealth-X profile ID")
    orbis_contact_id: Optional[str] = Field(None, description="Orbis contact ID")

    # Basic info
    title: Optional[str] = Field(None, description="Honorific title, e.g., 'Mr', 'Dr', 'Dame'")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    gender: Optional[str] = Field(None, description="Gender")
    nationality: Optional[str] = Field(None, description="Nationality")
    country_of_residence: Optional[str] = Field(None, description="Country of residence")
    city: Optional[str] = Field(None, description="City of residence")

    # Professional
    current_roles: list[Role] = Field(default_factory=list, description="Current professional roles")
    previous_roles: list[Role] = Field(default_factory=list, description="Previous professional roles")

    # Wealth (from Wealth-X/Wealth Monitor)
    net_worth: Optional[float] = Field(None, description="Estimated net worth")
    net_worth_currency: str = Field("USD", description="Currency of net worth figure")
    wealth_source: Optional[str] = Field(None, description="Source of wealth, e.g., 'Inherited', 'Self-made'")
    liquidity: Optional[float] = Field(None, description="Estimated liquid assets")

    # Interests/passions (from Wealth-X)
    interests: list[str] = Field(default_factory=list, description="Personal interests and hobbies")
    philanthropy: list[str] = Field(default_factory=list, description="Philanthropic causes and activities")

    # Connections
    known_associates: list[str] = Field(default_factory=list, description="Known business associates or connections")

    # Metadata
    sources: list[DataSource] = Field(default_factory=list, description="Data sources that provided information")
    is_existing_client: bool = Field(False, description="Whether this individual is already a client")
    last_updated: Optional[datetime] = Field(None, description="When this record was last updated")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "ind_001",
                "name": "John David Smith",
                "wealthx_id": "WX-123456",
                "orbis_contact_id": "P123456",
                "title": "Mr",
                "first_name": "John",
                "last_name": "Smith",
                "gender": "Male",
                "nationality": "British",
                "country_of_residence": "United Kingdom",
                "city": "London",
                "current_roles": [
                    {
                        "company_name": "ACME Technologies Ltd",
                        "title": "Chief Executive Officer",
                        "role_type": "Executive",
                        "is_current": True
                    }
                ],
                "previous_roles": [],
                "net_worth": 85000000,
                "net_worth_currency": "USD",
                "wealth_source": "Self-made",
                "liquidity": 25000000,
                "interests": ["Technology", "Sustainable investing", "Classical music"],
                "philanthropy": ["Education", "Climate change"],
                "known_associates": ["Jane Doe"],
                "sources": ["wealthx", "companies_house"],
                "is_existing_client": False,
                "last_updated": "2024-12-12T10:30:00Z"
            }
        }
