# normalize.py

import hashlib
import re


# ---------------------------
# INTERNAL HELPERS
# ---------------------------

def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:24]


def _normalize_string(value: str) -> str:
    if not value:
        return ""
    value = value.lower().strip()
    value = re.sub(r"\s+", " ", value)
    value = value.replace("«", "").replace("»", "").replace('"', "")
    return value


def _normalize_url(url: str) -> str:
    return url.rstrip("/").lower().strip()


# ---------------------------
# ENTITY TYPE DETECTION
# ---------------------------

def detect_entity_type_from_url(url: str) -> str:
    url = _normalize_url(url)

    if "/p/" in url:
        return "person"

    if "/c/" in url:
        return "company"

    return "unknown"


# ---------------------------
# ENTITY ID BUILDERS
# ---------------------------

def company_entity_id(country: str, tax_id: str) -> str:
    """
    Deterministic company ID based on official tax_id.
    Never hashed.
    """
    return f"company:{country}:{tax_id}"


def company_entity_id_from_url(country: str, url: str) -> str:
    """
    Extract tax_id from opendatabot company URL.
    """
    url = _normalize_url(url)
    tax_id = url.split("/")[-1]
    return company_entity_id(country, tax_id)


def person_entity_id(profile_url: str) -> str:
    """
    Person ID based on stable normalized profile URL.
    """
    normalized = _normalize_url(profile_url)
    return f"person:{_hash(normalized)}"


def foreign_company_entity_id(name: str, country: str) -> str:
    """
    For companies without tax_id.
    Uses normalized name hashing.
    """
    normalized_name = _normalize_string(name)
    return f"company:{country}:{_hash(normalized_name)}"