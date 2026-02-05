# parser.py
import re
from typing import Optional
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}


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
    import requests

    if is_html:
        html = url_or_html
    else:
        resp = requests.get(url_or_html, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")
    people = []
    people.extend(parse_owners_section(soup))
    people.extend(parse_director_section(soup))
    people.extend(parse_managers_section(soup))
    return people
