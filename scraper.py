from bs4 import BeautifulSoup
import requests
import csv
import time

BASE_URL = "https://www.njuskalo.hr/iznajmljivanje-stanova/zagreb"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def get_page(page_num):
    url = f"{BASE_URL}?page={page_num}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        print(f"Stranica {page_num} vratila status {res.status_code}")
        return None
    return res.text

def parse_page(html,locations, min_price, max_price):
    soup = BeautifulSoup(html, "html.parser")
    ads = soup.select("li.EntityList-item")
    results = []

    for ad in ads:
        title_tag = ad.select_one("h3.entity-title a.link")
        price_tag = ad.select_one(".price--hrk")
        desc_tag = ad.select_one(".entity-description-main")
        date_tag = ad.select_one(".entity-pub-date time")

        price_text=price_tag.get_text(strip=True).replace("€", "").replace(",","").strip() if price_tag else "0"
        try:
            price_value=int(price_text)
        except ValueError:
            price_value=0

        desc=desc_tag.get_text(" ",strip=True) if desc_tag else ""
        location_text=""
        if "Lokacija" in desc:
            location_text=desc.split("Lokacija:")[-1].strip()

        if (not locations or any(loc in location_text for loc in locations)) and (min_price <= price_value <= max_price):
            results.append({
                "title": title_tag.get_text(strip=True) if title_tag else None,
                "price": price_tag.get_text(strip=True) if price_tag else None,
                "description": desc_tag.get_text(" ", strip=True) if desc_tag else None,
                "date": date_tag.get_text(strip=True) if date_tag else None,
                "link": f"https://www.njuskalo.hr{title_tag['href']}" if title_tag else None
            })

    return results

def scrape_njuskalo(locations, min_price, max_price, pages):
    all_ads = []
    for page in range(1, pages+1):  
        print(f"➡️ Scraping stranica {page}...")
        html = get_page(page)
        if not html:
            break
        ads = parse_page(html, locations, min_price,max_price)
        all_ads.extend(ads)
        time.sleep(2)  

    filename="njuskalo_stanovi.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "price", "description", "date", "link"])
        writer.writeheader()
        writer.writerows(all_ads)

    return len(all_ads), filename
