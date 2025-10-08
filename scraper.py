# scraper.py
import requests
from bs4 import BeautifulSoup
import csv
import time
import re

BASE_URL = "https://www.njuskalo.hr/iznajmljivanje-stanova/zagreb"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get_page(page_num):
    url = f"{BASE_URL}?page={page_num}"
    res = requests.get(url, headers=HEADERS, timeout=15)
    if res.status_code != 200:
        print(f"⚠️ Stranica {page_num} vratila status {res.status_code}")
        return None
    return res.text


def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\xa0", " ")                 # NBSP -> space
    s = s.replace("–", "-").replace("—", "-")   # različite crtice -> -
    s = re.sub(r"\s+", " ", s)                 # collapse whitespace
    return s.strip()


def parse_price(price_text: str) -> int:
    if not price_text:
        return 0
    # ukloni non-digit znakove osim . i space
    txt = price_text.replace("\xa0", " ")
    # Pronađi prvi niz koji izgleda kao broj (npr. "1.200", "450", "1 200")
    m = re.search(r"(\d[\d\.\s]*)", txt)
    if not m:
        return 0
    num = m.group(1)
    # ukloni točke i razmake (tisućice), ostavi samo brojeve
    num = re.sub(r"[.\s]", "", num)
    try:
        return int(num)
    except ValueError:
        return 0


def fetch_location_from_ad(ad_url: str) -> str:
    """Fallback: otvori pojedinačni oglas i pokušaj dohvatiti lokaciju iz detalja oglasa."""
    try:
        r = requests.get(ad_url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        # pokušaj nekoliko selektora u detalju oglasa
        selectors = [
            "span.ClassifiedDetailBasicDetails-textWrapContainer",
            "div.ClassifiedDetailBasicDetails div",  # alternativno
            ".classified-detail__basic .classified-detail__value",
        ]
        for sel in selectors:
            tag = soup.select_one(sel)
            if tag and tag.get_text(strip=True):
                return normalize_text(tag.get_text(" ", strip=True))
    except Exception:
        return ""
    return ""


def extract_location_from_listing(ad) -> str:
    """Pokušaj izvući lokaciju direktno iz listing elementa (mnogi načini)."""
    # 1) eksplicitni span koji si spomenuo
    tag = ad.select_one("span.ClassifiedDetailBasicDetails-textWrapContainer")
    if tag and tag.get_text(strip=True):
        return normalize_text(tag.get_text(" ", strip=True))

    # 2) ponekad je lokacija u opisnom elementu; potraži 'Lokacija:'
    desc = ad.select_one(".entity-description-main")
    if desc:
        text = normalize_text(desc.get_text(" ", strip=True))
        if "Lokacija:" in text:
            # splitaj i uzmi što ide nakon 'Lokacija:'
            try:
                after = text.split("Lokacija:")[-1].strip()
                # ako ima <br> ili zarez, obično je u formatu "Kvart, Podkvart"
                return normalize_text(after.split("\n")[0])
            except Exception:
                return text

    # 3) drugi mogući tagovi
    alt = ad.select_one(".entity-description-subtitle, .entity-location, .entity-location-link")
    if alt and alt.get_text(strip=True):
        return normalize_text(alt.get_text(" ", strip=True))

    # ništa pronađeno
    return ""


def parse_page(html, locations=None, min_price=0, max_price=9999999, fetch_details=False, debug=False):
    """
    locations: lista substringova (npr. ["Maksimir", "Trešnjevka"])
    fetch_details: ako True, otvara pojedinačne oglase ako nije nađen location u listingu
    debug: ispis za prvih par oglasa
    """
    if locations is None:
        locations = []

    # normalize locations once (lowercase)
    norm_locs = [normalize_text(l).lower() for l in locations]

    soup = BeautifulSoup(html, "html.parser")
    ads = soup.select("li.EntityList-item")
    results = []
    dbg_count = 0

    for ad in ads:
        title_tag = ad.select_one("h3.entity-title a.link")
        price_tag = ad.select_one(".price--hrk, .price--eur, .price, strong.price, .entity-price")
        date_tag = ad.select_one(".entity-pub-date time")
        link = None
        if title_tag and title_tag.has_attr("href"):
            link = "https://www.njuskalo.hr" + title_tag["href"]

        title = title_tag.get_text(strip=True) if title_tag else ""
        price_text = price_tag.get_text(" ", strip=True) if price_tag else ""
        price_value = parse_price(price_text)

        # pokušaj direktno iz listing elementa
        location_text = extract_location_from_listing(ad)

        # fallback: ako nema location u listingu i korisnik traži fetch_details
        if not location_text and fetch_details and link:
            location_text = fetch_location_from_ad(link)

        location_norm = normalize_text(location_text).lower()

        # filtriranje po lokaciji: ako korisnik navede lokacije, zahtjevaj bar jednu podudarnost
        loc_ok = True
        if norm_locs:
            loc_ok = any(loc in location_norm for loc in norm_locs)

        price_ok = (min_price <= price_value <= max_price)

        if debug and dbg_count < 10:
            print("---- DEBUG OGLAS ----")
            print("Naslov:", title)
            print("Link:", link)
            print("Cijena (tekst):", price_text, "=>", price_value)
            print("Lokacija (raw):", repr(location_text))
            print("Lokacija (norm):", location_norm)
            print("Loc match:", loc_ok, "Price match:", price_ok)
            print("---------------------")
            dbg_count += 1

        if loc_ok and price_ok:
            desc = ad.select_one(".entity-description-main")
            results.append({
                "title": title,
                "price": price_text,
                "description": desc.get_text(" ", strip=True) if desc else "",
                "location": location_text,
                "date": date_tag.get_text(strip=True) if date_tag else None,
                "link": link
            })

    return results


def scrape_njuskalo(locations, min_price, max_price, pages, fetch_details=False, debug=False):
    all_ads = []
    for page in range(1, pages + 1):
        if debug:
            print(f"➡️ Getting page {page} ...")
        html = get_page(page)
        if not html:
            break
        ads = parse_page(html, locations=locations, min_price=min_price, max_price=max_price,
                         fetch_details=fetch_details, debug=debug)
        all_ads.extend(ads)
        time.sleep(2)

    filename = "njuskalo_stanovi.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "price", "description", "location", "date", "link"])
        writer.writeheader()
        writer.writerows(all_ads)

    return len(all_ads), filename

if __name__ == "__main__":
    # test: samo prva stranica, debug on, bez fetch_details
    cnt, file = scrape_njuskalo(
    ["maksimir", "trešnjevka", "donji grad", "črnomerec", "novi zagreb"],
    0, 3000, pages=2, debug=False
)
print("Found:", cnt)