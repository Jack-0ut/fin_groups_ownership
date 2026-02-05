# crawler.py
from .normalize import (
    company_entity_id,
    person_entity_id,
    foreign_company_entity_id,
)
from .parser import parse_owners
from fin_groups.db import OwnershipDB

BASE_URL = "https://opendatabot.ua/c/{}"

class CompanyCrawler:
    def __init__(self, db: OwnershipDB, country: str = "UA"):
        self.db = db
        self.country = country

    def crawl_company(self, tax_id: str) -> list[dict]:
        company_url = BASE_URL.format(tax_id)
        company_id = company_entity_id(self.country, tax_id)

        self._store_company(company_id, tax_id, company_url)

        owners = parse_owners(company_url)

        for o in owners:
            owner_id, owner_type = self._normalize_owner(o)

            self._store_owner(owner_id, owner_type, o)
            self._store_relationship(owner_id, company_id, o, company_url)

        print(owners)
        return owners

    # ---------- internals ----------

    def _store_company(self, company_id: str, tax_id: str, url: str):
        self.db.upsert_entity({
            "entity_id": company_id,
            "entity_type": "company",
            "name": f"Company {tax_id}",
            "country": self.country,
            "tax_id": tax_id,
            "source_url": url,
        })

    def _normalize_owner(self, o: dict) -> tuple[str, str]:
        if o.get("profile_link"):
            return person_entity_id(o["profile_link"]), "person"

        if o.get("country") and o["country"] != "Україна":
            return (
                foreign_company_entity_id(o["name"], o["country"]),
                "company",
            )

        return foreign_company_entity_id(o["name"], "UA"), "company"

    def _store_owner(self, entity_id: str, entity_type: str, o: dict):
        self.db.upsert_entity({
            "entity_id": entity_id,
            "entity_type": entity_type,
            "name": o["name"],
            "country": o.get("country"),
            "tax_id": None,
            "source_url": o.get("profile_link"),
        })

    def _store_relationship(
        self,
        owner_id: str,
        company_id: str,
        o: dict,
        source_url: str,
    ):
        role = (o.get("role") or "").lower()

        if role == "director":
            control_level = "management"
        elif "бенефіціар" in role:
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
