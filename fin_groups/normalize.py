# normalize.py
import hashlib

def _hash(value: str) -> str:
    return hashlib.sha256(value.lower().strip().encode()).hexdigest()[:24]

def company_entity_id(country: str, tax_id: str) -> str:
    return f"company:{country}:{tax_id}"

def person_entity_id(profile_url: str) -> str:
    return f"person:{_hash(profile_url)}"

def foreign_company_entity_id(name: str, country: str) -> str:
    return f"company:{country}:{_hash(name)}"
