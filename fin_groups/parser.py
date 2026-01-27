# parser.py
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}

def parse_owners(url: str) -> list[dict]:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    owners = []

    dt = soup.find("dt", string=re.compile(r"Власники"))
    if not dt:
        return owners

    for dd in dt.find_next_siblings("dd"):
        name_tag = dd.find("a") or dd.find("p")

        svg = dd.find("svg", class_=re.compile("flag"))
        country = svg.next_sibling.strip() if svg and svg.next_sibling else None

        role_p = dd.find("p", class_="small")
        data = dd.find("data")

        owners.append({
            "name": name_tag.get_text(strip=True) if name_tag else None,
            "profile_link": (
                f"https://opendatabot.ua{name_tag['href']}"
                if name_tag and name_tag.name == "a" and name_tag.has_attr("href")
                else None
            ),
            "country": country,
            "role": role_p.get_text(strip=True) if role_p else None,
            "amount_uah": int(data["value"]) if data else None,
            "share_percent": (
                int(m.group(1))
                if data and (m := re.search(r"(\d+)%", data.get_text()))
                else None
            )
        })

    return owners
