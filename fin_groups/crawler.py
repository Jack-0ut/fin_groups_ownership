# crawler.py

from .normalize import (
    company_entity_id,
    company_entity_id_from_url,
    person_entity_id,
    foreign_company_entity_id,
    detect_entity_type_from_url,
)
from .parser import parse_owners, parse_company_metadata
from fin_groups.db import OwnershipDB


BASE_URL = "https://opendatabot.ua/c/{}"


class CompanyCrawler:
    def __init__(self, db: OwnershipDB, country: str = "UA"):
        self.db = db
        self.country = country

    # ---------------------------------------
    # PUBLIC
    # ---------------------------------------

    def crawl_company(self, tax_id: str, print_owners: bool = False) -> list[dict]:
        company_url = BASE_URL.format(tax_id)
        company_id = company_entity_id(self.country, tax_id)

        company_info = parse_company_metadata(company_url)
        self._store_company(company_id, tax_id, company_url, company_info)

        owners = parse_owners(company_url)

        for o in owners:
            owner_id, owner_type = self._normalize_owner(o)

            self._store_owner(owner_id, owner_type, o)
            self._store_relationship(owner_id, company_id, o, company_url)

        if print_owners:
            print(owners)

        return owners

    # ---------------------------------------
    # INTERNAL
    # ---------------------------------------

    def _store_company(self, company_id: str, tax_id: str, url: str, company_info: dict | None = None):
        entity = {
            "entity_id": company_id,
            "entity_type": "company",
            "name": f"Company {tax_id}",
            "country": self.country,
            "tax_id": tax_id,
            "source_url": url,
            "address": None,
            "founding_date": None,
            "status": None,
        }

        if company_info:
            entity["name"] = company_info.get("name") or entity["name"]
            entity["address"] = company_info.get("address")
            entity["founding_date"] = company_info.get("founding_date")
            entity["status"] = company_info.get("status")

        self.db.upsert_entity(entity)

    def _normalize_owner(self, o: dict) -> tuple[str, str]:
        """
        Correct entity type detection based on URL.
        Prevents company→person misclassification.
        """
        link = o.get("profile_link")

        if link:
            entity_type = detect_entity_type_from_url(link)

            if entity_type == "person":
                return person_entity_id(link), "person"

            if entity_type == "company":
                return (
                    company_entity_id_from_url(self.country, link),
                    "company",
                )

        # fallback for entities without profile_link
        country = o.get("country") or self.country

        return (
            foreign_company_entity_id(o["name"], country),
            "company",
        )

    def _store_owner(self, entity_id: str, entity_type: str, o: dict):
        self.db.upsert_entity({
            "entity_id": entity_id,
            "entity_type": entity_type,
            "name": o["name"],
            "country": o.get("country"),
            "tax_id": None,
            "source_url": o.get("profile_link"),
        })

    def _store_relationship(self, owner_id, company_id, o, source_url):
        role = (o.get("role") or "").lower()

        if any(k in role for k in ["директор", "керівник", "підписант"]):
            control_level = "management"
        elif any(k in role for k in ["бенефіціар", "ubo"]):
            control_level = "beneficial"
        else:
            control_level = "direct"

        self.db.upsert_ownership({
            "owner_id": owner_id,
            "owned_id": company_id,
            "role": o.get("role"),
            "share_percent": o.get("share_percent"),
            "capital_uah": o.get("amount_uah"),
            "control_level": control_level,
            "source": "opendatabot",
            "source_url": source_url,
        })