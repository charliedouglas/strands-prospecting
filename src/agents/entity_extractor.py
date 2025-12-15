"""
Entity Extractor for the prospecting system.

Extracts Company and Individual entities from raw data source responses
and deduplicates them across multiple sources.
"""

import logging
import hashlib
from datetime import datetime
from typing import Optional

from src.models import (
    SearchResult,
    DataSource,
    Company,
    Individual,
    Role,
)

logger = logging.getLogger(__name__)


class EntityExtractor:
    """
    Extracts and deduplicates entities from raw search results.

    Parses source-specific data formats and creates normalized
    Company and Individual entities.
    """

    def extract_entities(
        self,
        results: list[SearchResult]
    ) -> tuple[list[Company], list[Individual]]:
        """
        Extract all entities from search results.

        Args:
            results: List of SearchResult objects from executor

        Returns:
            Tuple of (companies, individuals) lists
        """
        companies: dict[str, Company] = {}  # keyed by normalized name
        individuals: dict[str, Individual] = {}  # keyed by normalized name

        for result in results:
            if not result.success or result.data is None:
                continue

            try:
                extracted_companies, extracted_individuals = self._extract_from_source(
                    result.source,
                    result.data
                )

                # Merge companies
                for company in extracted_companies:
                    key = self._normalize_company_key(company.name)
                    if key in companies:
                        companies[key] = self._merge_companies(companies[key], company)
                    else:
                        companies[key] = company

                # Merge individuals
                for individual in extracted_individuals:
                    key = self._normalize_individual_key(individual.name)
                    if key in individuals:
                        individuals[key] = self._merge_individuals(individuals[key], individual)
                    else:
                        individuals[key] = individual

            except Exception as e:
                logger.warning(f"Error extracting from {result.source.value}: {e}")
                continue

        logger.info(
            f"Extracted {len(companies)} companies, {len(individuals)} individuals"
        )
        return list(companies.values()), list(individuals.values())

    def _extract_from_source(
        self,
        source: DataSource,
        data: dict | list
    ) -> tuple[list[Company], list[Individual]]:
        """
        Extract entities based on data source type.

        Args:
            source: The data source
            data: Raw data from the source

        Returns:
            Tuple of (companies, individuals)
        """
        extractors = {
            DataSource.COMPANIES_HOUSE: self._extract_from_companies_house,
            DataSource.ORBIS: self._extract_from_orbis,
            DataSource.CRUNCHBASE: self._extract_from_crunchbase,
            DataSource.PITCHBOOK: self._extract_from_pitchbook,
            DataSource.DUN_BRADSTREET: self._extract_from_dnb,
            DataSource.WEALTHX: self._extract_from_wealthx,
            DataSource.WEALTH_MONITOR: self._extract_from_wealth_monitor,
            DataSource.SERPAPI: self._extract_from_serpapi,
            DataSource.INTERNAL_CRM: self._extract_from_crm,
        }

        extractor = extractors.get(source)
        if extractor:
            return extractor(data)

        logger.debug(f"No extractor for source: {source.value}")
        return [], []

    def _extract_from_companies_house(
        self,
        data: dict
    ) -> tuple[list[Company], list[Individual]]:
        """Extract from Companies House response."""
        companies = []
        individuals = []

        # Handle search results
        if "items" in data:
            for item in data["items"]:
                company = self._parse_ch_company(item)
                if company:
                    companies.append(company)

        # Handle single company profile
        elif "company_number" in data:
            company = self._parse_ch_company(data)
            if company:
                companies.append(company)

        # Handle officers list
        if "items" in data and data.get("kind") == "officer-list":
            for officer in data["items"]:
                individual = self._parse_ch_officer(officer)
                if individual:
                    individuals.append(individual)

        return companies, individuals

    def _parse_ch_company(self, item: dict) -> Optional[Company]:
        """Parse a Companies House company record."""
        name = item.get("company_name") or item.get("title")
        if not name:
            return None

        company_number = item.get("company_number")

        # Parse address
        address = item.get("registered_office_address") or item.get("address", {})
        city = address.get("locality")

        return Company(
            id=f"ch_{company_number}" if company_number else self._generate_id(name),
            name=name,
            companies_house_number=company_number,
            country="GB",
            city=city,
            address=self._format_address(address),
            company_type=item.get("type") or item.get("company_type"),
            status=item.get("company_status"),
            incorporation_date=item.get("date_of_creation"),
            sic_codes=item.get("sic_codes", []),
            sources=[DataSource.COMPANIES_HOUSE],
            last_updated=datetime.now()
        )

    def _parse_ch_officer(self, officer: dict) -> Optional[Individual]:
        """Parse a Companies House officer record."""
        name = officer.get("name")
        if not name:
            return None

        # Parse name components if available
        first_name = None
        last_name = None
        if ", " in name:
            # Format: "SMITH, John David"
            parts = name.split(", ")
            last_name = parts[0].title()
            first_name = parts[1] if len(parts) > 1 else None

        dob = officer.get("date_of_birth", {})

        return Individual(
            id=f"ch_officer_{self._generate_id(name)}",
            name=name.title() if name.isupper() else name,
            first_name=first_name,
            last_name=last_name,
            nationality=officer.get("nationality"),
            country_of_residence=officer.get("country_of_residence"),
            current_roles=[
                Role(
                    company_name="Unknown",  # Will be enriched by context
                    title=officer.get("officer_role", "Director").title(),
                    role_type=officer.get("officer_role", "Director").title(),
                    start_date=officer.get("appointed_on"),
                    end_date=officer.get("resigned_on"),
                    is_current=officer.get("resigned_on") is None
                )
            ] if officer.get("officer_role") else [],
            sources=[DataSource.COMPANIES_HOUSE],
            last_updated=datetime.now()
        )

    def _extract_from_orbis(
        self,
        data: dict
    ) -> tuple[list[Company], list[Individual]]:
        """Extract from Orbis response."""
        companies = []
        individuals = []

        # Handle company search results
        if "results" in data:
            for item in data["results"]:
                company = self._parse_orbis_company(item)
                if company:
                    companies.append(company)

        # Handle single company
        elif "bvd_id" in data:
            company = self._parse_orbis_company(data)
            if company:
                companies.append(company)

        # Handle directors response
        if "directors" in data:
            for director in data["directors"]:
                individual = self._parse_orbis_director(director, data.get("company_name"))
                if individual:
                    individuals.append(individual)

        # Handle ownership response
        if "shareholders" in data:
            for shareholder in data["shareholders"]:
                if shareholder.get("type") == "Individual":
                    individual = Individual(
                        id=f"orbis_shareholder_{self._generate_id(shareholder.get('name', ''))}",
                        name=shareholder.get("name", "Unknown"),
                        sources=[DataSource.ORBIS],
                        last_updated=datetime.now()
                    )
                    individuals.append(individual)

        return companies, individuals

    def _parse_orbis_company(self, item: dict) -> Optional[Company]:
        """Parse an Orbis company record."""
        name = item.get("name")
        if not name:
            return None

        address = item.get("registered_address", {})
        national_ids = item.get("national_ids", [])
        ch_number = None
        for nid in national_ids:
            if nid.get("type") == "Companies House":
                ch_number = nid.get("value")
                break

        industry = item.get("industry", {})

        return Company(
            id=f"orbis_{item.get('bvd_id', self._generate_id(name))}",
            name=name,
            bvd_id=item.get("bvd_id"),
            companies_house_number=ch_number,
            country=item.get("country", "GB"),
            city=address.get("city"),
            address=self._format_address(address),
            industry=industry.get("primary_description") if isinstance(industry, dict) else None,
            status=item.get("status"),
            incorporation_date=item.get("incorporation_date"),
            revenue=item.get("operating_revenue"),
            revenue_currency=item.get("operating_revenue_currency", "GBP"),
            employee_count=item.get("employees"),
            sources=[DataSource.ORBIS],
            last_updated=datetime.now()
        )

    def _parse_orbis_director(self, director: dict, company_name: str = None) -> Optional[Individual]:
        """Parse an Orbis director record."""
        name = director.get("name")
        if not name:
            return None

        return Individual(
            id=f"orbis_dir_{director.get('contact_id', self._generate_id(name))}",
            name=name,
            orbis_contact_id=director.get("contact_id"),
            title=director.get("title"),
            nationality=director.get("nationality"),
            current_roles=[
                Role(
                    company_name=company_name or "Unknown",
                    title=director.get("role", "Director"),
                    role_type="Director",
                    start_date=director.get("appointment_date"),
                    end_date=director.get("resignation_date"),
                    is_current=director.get("is_current", True)
                )
            ] if company_name else [],
            sources=[DataSource.ORBIS],
            last_updated=datetime.now()
        )

    def _extract_from_crunchbase(
        self,
        data: dict
    ) -> tuple[list[Company], list[Individual]]:
        """Extract from Crunchbase response."""
        companies = []
        individuals = []

        # Handle funding round search
        if "entities" in data:
            for entity in data["entities"]:
                props = entity.get("properties", {})
                org = props.get("funded_organization_identifier", {})
                if org:
                    company = Company(
                        id=f"cb_{org.get('uuid', self._generate_id(org.get('value', '')))}",
                        name=org.get("value", "Unknown"),
                        crunchbase_uuid=org.get("uuid"),
                        country="GB",  # Default, may need refinement
                        total_funding=props.get("money_raised", {}).get("value_usd"),
                        funding_currency="USD",
                        last_funding_round=props.get("investment_type"),
                        last_funding_date=props.get("announced_on"),
                        last_funding_amount=props.get("money_raised", {}).get("value"),
                        investors=[
                            inv.get("value")
                            for inv in props.get("investor_identifiers", [])
                        ],
                        sources=[DataSource.CRUNCHBASE],
                        last_updated=datetime.now()
                    )
                    companies.append(company)

        # Handle organization details
        elif "properties" in data:
            props = data["properties"]
            identifier = props.get("identifier", {})

            location = props.get("location_identifiers", [])
            country = "GB"
            city = None
            for loc in location:
                if loc.get("location_type") == "country":
                    country = loc.get("value", "GB")
                elif loc.get("location_type") == "city":
                    city = loc.get("value")

            company = Company(
                id=f"cb_{identifier.get('uuid', '')}",
                name=identifier.get("value", "Unknown"),
                crunchbase_uuid=identifier.get("uuid"),
                country=country,
                city=city,
                website=props.get("website", {}).get("value"),
                industry=props.get("categories", [{}])[0].get("value") if props.get("categories") else None,
                total_funding=props.get("funding_total", {}).get("value_usd"),
                funding_currency="USD",
                sources=[DataSource.CRUNCHBASE],
                last_updated=datetime.now()
            )
            companies.append(company)

        return companies, individuals

    def _extract_from_pitchbook(
        self,
        data: dict
    ) -> tuple[list[Company], list[Individual]]:
        """Extract from PitchBook response."""
        companies = []
        individuals = []

        # Handle deals search
        if "deals" in data:
            for deal in data["deals"]:
                company_data = deal.get("company", {})
                if company_data:
                    company = Company(
                        id=f"pb_{company_data.get('company_id', '')}",
                        name=company_data.get("name", "Unknown"),
                        pitchbook_id=company_data.get("company_id"),
                        country="GB",
                        city=company_data.get("hq_location", "").split(",")[0] if company_data.get("hq_location") else None,
                        website=company_data.get("website"),
                        industry=company_data.get("primary_industry"),
                        employee_count=company_data.get("employee_count"),
                        total_funding=deal.get("deal_size"),
                        funding_currency=deal.get("deal_size_currency", "GBP"),
                        last_funding_round=deal.get("series"),
                        last_funding_date=deal.get("deal_date"),
                        last_funding_amount=deal.get("deal_size"),
                        investors=[
                            inv.get("name")
                            for inv in deal.get("investors", [])
                        ],
                        sources=[DataSource.PITCHBOOK],
                        last_updated=datetime.now()
                    )
                    companies.append(company)

        # Handle company profile
        elif "company_id" in data:
            hq = data.get("hq_location", {})
            city = hq.get("city") if isinstance(hq, dict) else (hq.split(",")[0] if isinstance(hq, str) else None)

            company = Company(
                id=f"pb_{data.get('company_id', '')}",
                name=data.get("name", "Unknown"),
                pitchbook_id=data.get("company_id"),
                country="GB",
                city=city,
                website=data.get("website"),
                industry=data.get("primary_industry"),
                employee_count=data.get("employee_count"),
                total_funding=data.get("total_raised"),
                funding_currency=data.get("total_raised_currency", "GBP"),
                last_funding_round=data.get("last_financing_type"),
                last_funding_date=data.get("last_financing_date"),
                last_funding_amount=data.get("last_financing_size"),
                sources=[DataSource.PITCHBOOK],
                last_updated=datetime.now()
            )
            companies.append(company)

            # Extract executives
            for exec_data in data.get("executives", []):
                individual = Individual(
                    id=f"pb_{exec_data.get('person_id', self._generate_id(exec_data.get('name', '')))}",
                    name=exec_data.get("name", "Unknown"),
                    current_roles=[
                        Role(
                            company_name=data.get("name", "Unknown"),
                            company_id=data.get("company_id"),
                            title=exec_data.get("title", "Executive"),
                            role_type="Executive",
                            start_date=exec_data.get("start_date"),
                            is_current=True
                        )
                    ],
                    sources=[DataSource.PITCHBOOK],
                    last_updated=datetime.now()
                )
                individuals.append(individual)

        return companies, individuals

    def _extract_from_dnb(
        self,
        data: dict
    ) -> tuple[list[Company], list[Individual]]:
        """Extract from D&B response."""
        companies = []
        individuals = []

        org = data.get("organization", {})
        if not org:
            # Check for match candidates
            candidates = data.get("matchCandidates", [])
            for candidate in candidates:
                org = candidate.get("organization", {})
                if org:
                    break

        if org:
            address = org.get("primaryAddress", {})

            company = Company(
                id=f"dnb_{org.get('duns', '')}",
                name=org.get("primaryName", "Unknown"),
                duns_number=org.get("duns"),
                country=address.get("addressCountry", {}).get("isoAlpha2Code", "GB"),
                city=address.get("addressLocality", {}).get("name"),
                address=address.get("streetAddress", {}).get("line1"),
                status=org.get("dunsControlStatus", {}).get("operatingStatus", {}).get("description"),
                incorporation_date=org.get("incorporatedDate"),
                employee_count=org.get("numberOfEmployees", [{}])[0].get("value") if org.get("numberOfEmployees") else None,
                sources=[DataSource.DUN_BRADSTREET],
                last_updated=datetime.now()
            )
            companies.append(company)

            # Extract principals
            for principal in data.get("principals", []):
                individual = Individual(
                    id=f"dnb_principal_{self._generate_id(principal.get('fullName', ''))}",
                    name=principal.get("fullName", "Unknown"),
                    title=principal.get("namePrefix"),
                    first_name=principal.get("givenName"),
                    last_name=principal.get("familyName"),
                    current_roles=[
                        Role(
                            company_name=org.get("primaryName", "Unknown"),
                            title=principal.get("jobTitles", [{}])[0].get("title", "Executive") if principal.get("jobTitles") else "Executive",
                            role_type="Executive",
                            is_current=True
                        )
                    ],
                    sources=[DataSource.DUN_BRADSTREET],
                    last_updated=datetime.now()
                )
                individuals.append(individual)

        return companies, individuals

    def _extract_from_wealthx(
        self,
        data: dict
    ) -> tuple[list[Company], list[Individual]]:
        """Extract from Wealth-X response."""
        companies = []
        individuals = []

        # Handle profile search
        profiles = data.get("profiles", [data]) if "profiles" in data else [data] if "wealthx_id" in data else []

        for profile in profiles:
            if not profile.get("name"):
                continue

            net_worth = profile.get("net_worth", {})

            individual = Individual(
                id=f"wx_{profile.get('wealthx_id', self._generate_id(profile.get('name', '')))}",
                name=profile.get("name"),
                wealthx_id=profile.get("wealthx_id"),
                title=profile.get("title"),
                first_name=profile.get("first_name"),
                last_name=profile.get("last_name"),
                gender=profile.get("gender"),
                nationality=profile.get("nationality"),
                country_of_residence=profile.get("country_of_residence"),
                city=profile.get("city"),
                net_worth=net_worth.get("value") if isinstance(net_worth, dict) else net_worth,
                net_worth_currency=net_worth.get("currency", "USD") if isinstance(net_worth, dict) else "USD",
                wealth_source=profile.get("wealth_source"),
                liquidity=profile.get("liquidity", {}).get("value") if isinstance(profile.get("liquidity"), dict) else profile.get("liquidity"),
                interests=profile.get("interests", []),
                philanthropy=profile.get("philanthropy", {}).get("causes", []) if isinstance(profile.get("philanthropy"), dict) else [],
                sources=[DataSource.WEALTHX],
                last_updated=datetime.now()
            )

            # Extract roles from positions
            for position in profile.get("current_positions", []):
                individual.current_roles.append(
                    Role(
                        company_name=position.get("company", "Unknown"),
                        title=position.get("title", "Unknown"),
                        role_type="Executive",
                        start_date=str(position.get("start_year")) if position.get("start_year") else None,
                        is_current=True
                    )
                )

            individuals.append(individual)

        return companies, individuals

    def _extract_from_wealth_monitor(
        self,
        data: dict
    ) -> tuple[list[Company], list[Individual]]:
        """Extract from Wealth Monitor response."""
        companies = []
        individuals = []

        for profile in data.get("individuals", []):
            individual = Individual(
                id=f"wm_{profile.get('wm_id', self._generate_id(profile.get('name', '')))}",
                name=profile.get("name", "Unknown"),
                country_of_residence="United Kingdom",
                city=profile.get("region"),
                net_worth=profile.get("estimated_net_worth"),
                net_worth_currency="USD",
                sources=[DataSource.WEALTH_MONITOR],
                last_updated=datetime.now()
            )

            # Extract roles from directorships
            for directorship in profile.get("directorships", []):
                individual.current_roles.append(
                    Role(
                        company_name=directorship.get("company_name", "Unknown"),
                        company_id=directorship.get("company_number"),
                        title=directorship.get("role", "Director"),
                        role_type="Director",
                        start_date=directorship.get("appointed"),
                        is_current=directorship.get("status") == "Active"
                    )
                )

            individuals.append(individual)

        return companies, individuals

    def _extract_from_serpapi(
        self,
        data: dict
    ) -> tuple[list[Company], list[Individual]]:
        """Extract from SerpAPI response - primarily for news context."""
        # SerpAPI returns news/search results, not structured entity data
        # Could potentially extract company mentions from knowledge_graph
        companies = []
        individuals = []

        kg = data.get("knowledge_graph", {})
        if kg and kg.get("type") in ["Technology company", "Company", "Organization"]:
            company = Company(
                id=f"serp_{self._generate_id(kg.get('title', ''))}",
                name=kg.get("title", "Unknown"),
                country="GB",
                industry=kg.get("type"),
                sources=[DataSource.SERPAPI],
                last_updated=datetime.now()
            )
            companies.append(company)

        return companies, individuals

    def _extract_from_crm(
        self,
        data: dict
    ) -> tuple[list[Company], list[Individual]]:
        """Extract from CRM response - marks existing clients."""
        # CRM data is used for filtering, not entity creation
        # Return empty lists - CRM info is used by sufficiency checker
        return [], []

    def _normalize_company_key(self, name: str) -> str:
        """Create normalized key for company deduplication."""
        if not name:
            return ""
        # Remove common suffixes and normalize
        normalized = name.upper().strip()
        for suffix in [" LTD", " LIMITED", " PLC", " INC", " CORP", " LLC"]:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
        return normalized.strip()

    def _normalize_individual_key(self, name: str) -> str:
        """Create normalized key for individual deduplication."""
        if not name:
            return ""
        return name.upper().strip()

    def _generate_id(self, text: str) -> str:
        """Generate a short hash ID from text."""
        return hashlib.md5(text.encode()).hexdigest()[:12]

    def _format_address(self, address: dict) -> Optional[str]:
        """Format address dict into string."""
        if not address:
            return None
        parts = [
            address.get("line1") or address.get("address_line_1"),
            address.get("line2") or address.get("address_line_2"),
            address.get("locality") or address.get("city"),
            address.get("postal_code") or address.get("postcode"),
            address.get("country")
        ]
        return ", ".join(p for p in parts if p)

    def _merge_companies(self, existing: Company, new: Company) -> Company:
        """Merge two company records, preferring non-None values."""
        merged_data = existing.model_dump()
        new_data = new.model_dump()

        for key, value in new_data.items():
            if key == "sources":
                # Combine sources
                merged_data["sources"] = list(set(existing.sources + new.sources))
            elif key == "investors":
                # Combine investors
                merged_data["investors"] = list(set(existing.investors + new.investors))
            elif key == "trading_names":
                # Combine trading names
                merged_data["trading_names"] = list(set(existing.trading_names + new.trading_names))
            elif key == "sic_codes":
                # Combine SIC codes
                merged_data["sic_codes"] = list(set(existing.sic_codes + new.sic_codes))
            elif value is not None and merged_data.get(key) is None:
                # Take new value if existing is None
                merged_data[key] = value

        return Company(**merged_data)

    def _merge_individuals(self, existing: Individual, new: Individual) -> Individual:
        """Merge two individual records, preferring non-None values."""
        merged_data = existing.model_dump()
        new_data = new.model_dump()

        for key, value in new_data.items():
            if key == "sources":
                merged_data["sources"] = list(set(existing.sources + new.sources))
            elif key == "current_roles":
                # Combine roles, avoiding duplicates
                existing_roles = {(r.company_name, r.title) for r in existing.current_roles}
                for role in new.current_roles:
                    if (role.company_name, role.title) not in existing_roles:
                        merged_data["current_roles"].append(role.model_dump())
            elif key == "interests":
                merged_data["interests"] = list(set(existing.interests + new.interests))
            elif key == "philanthropy":
                merged_data["philanthropy"] = list(set(existing.philanthropy + new.philanthropy))
            elif key == "known_associates":
                merged_data["known_associates"] = list(set(existing.known_associates + new.known_associates))
            elif value is not None and merged_data.get(key) is None:
                merged_data[key] = value

        return Individual(**merged_data)
