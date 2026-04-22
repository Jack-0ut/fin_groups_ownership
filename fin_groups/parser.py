# parser.py
import re
from typing import Optional
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}


def _load_html(url_or_html: str, is_html: bool = False) -> str:
    if is_html:
        return url_or_html
    import requests

    resp = requests.get(url_or_html, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_share_percent(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def parse_person_dd(dd, default_role: Optional[str] = None) -> Optional[dict]:
    """Extract person/director/manager from <dd>"""
    name_tag = dd.find("a") or dd.find("p")
    if not name_tag:
        return None

    role_p = dd.find("p", class_="small")
    return {
        "name": name_tag.get_text(strip=True),
        "profile_link": (
            f"https://opendatabot.ua{name_tag['href']}"
            if name_tag.name == "a" and name_tag.has_attr("href")
            else None
        ),
        "role": role_p.get_text(strip=True) if role_p else default_role,
        "raw_text": dd.get_text(" ", strip=True),
    }


def parse_owners_section(soup):
    people = []
    dt = soup.find("dt", string=re.compile(r"Власники"))
    if not dt:
        return people

    for dd in dt.find_next_siblings("dd"):
        p = parse_person_dd(dd, default_role="owner")
        if not p:
            continue

        data = dd.find("data")
        p["amount_uah"] = int(data["value"]) if data and data.has_attr("value") else None
        p["share_percent"] = parse_share_percent(data.get_text()) if data else None

        # Country
        svg = dd.find("svg", class_=re.compile("flag"))
        p["country"] = svg.next_sibling.strip() if svg and svg.next_sibling else None

        people.append(p)
    return people


def parse_director_section(soup):
    people = []
    dt = soup.find("dt", string=re.compile(r"Директор"))
    if not dt:
        return people
    dd = dt.find_next_sibling("dd")
    if not dd:
        return people
    p = parse_person_dd(dd, default_role="director")
    if p:
        p["amount_uah"] = None
        p["share_percent"] = 0.0
        p["country"] = "Україна"
        people.append(p)
    return people


def parse_managers_section(soup):
    people = []
    dt = soup.find("dt", string=re.compile(r"Керівники"))
    if not dt:
        return people

    for dd in dt.find_next_siblings("dd"):
        p = parse_person_dd(dd)
        if not p:
            continue
        p["amount_uah"] = None
        p["share_percent"] = 0.0
        p["country"] = "Україна"
        people.append(p)
    return people


def parse_owners(url_or_html: str, is_html: bool = False) -> list[dict]:
    """
    url_or_html: if is_html=False -> url to fetch
                 if is_html=True -> raw HTML string
    """
    html = _load_html(url_or_html, is_html)
    soup = BeautifulSoup(html, "html.parser")
    people = []
    people.extend(parse_owners_section(soup))
    people.extend(parse_director_section(soup))
    people.extend(parse_managers_section(soup))
    return people


def parse_company_info(soup) -> dict:
    info = {}

    name_meta = soup.find("meta", itemprop="name")
    if name_meta and name_meta.get("content"):
        info["name"] = name_meta["content"].strip()
    else:
        name_dt = soup.find("dt", string=re.compile(r"Повна назва"))
        if name_dt:
            name_dd = name_dt.find_next_sibling("dd")
            if name_dd:
                info["name"] = name_dd.get_text(" ", strip=True)

    address_dd = soup.find(attrs={"data-odb-prop": "address"})
    if address_dd:
        info["address"] = address_dd.get_text(" ", strip=True)

    founding_dd = soup.find(attrs={"data-odb-prop": "foundingDate"})
    if founding_dd:
        time_tag = founding_dd.find("time", attrs={"datetime": True})
        if time_tag:
            info["founding_date"] = time_tag["datetime"].strip()

    if "founding_date" not in info:
        time_tag = soup.find("time", attrs={"datetime": True})
        if time_tag:
            info["founding_date"] = time_tag["datetime"].strip()

    status_div = soup.find("div", class_=re.compile(r"alert"))
    if status_div:
        status_text = status_div.get_text(" ", strip=True)
        m = re.search(r"Статус\s*компанії\s*[:\-–]\s*(.+)$", status_text, re.IGNORECASE)
        if m:
            info["status"] = m.group(1).strip()

    return info


def parse_company_metadata(url_or_html: str, is_html: bool = False) -> dict:
    html = _load_html(url_or_html, is_html)
    soup = BeautifulSoup(html, "html.parser")
    return parse_company_info(soup)
