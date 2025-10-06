import requests
from bs4 import BeautifulSoup
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
        print(f"⚠️ Stranica {page_num} vratila status {res.status_code}")
        return None
    return res.text

def parse_page(html):
    soup = BeautifulSoup(html, "html.parser")
    ads = soup.select("li.EntityList-item")
    results = []

    for ad in ads:
        title_tag = ad.select_one("h3.entity-title a.link")
        price_tag = ad.select_one(".price--hrk")
        desc_tag = ad.select_one(".entity-description-main")
        date_tag = ad.select_one(".entity-pub-date time")

        results.append({
            "title": title_tag.get_text(strip=True) if title_tag else None,
            "price": price_tag.get_text(strip=True) if price_tag else None,
            "description": desc_tag.get_text(" ", strip=True) if desc_tag else None,
            "date": date_tag.get_text(strip=True) if date_tag else None,
            "link": f"https://www.njuskalo.hr{title_tag['href']}" if title_tag else None
        })

    return results

def main():
    all_ads = []
    for page in range(1, 6):  
        print(f"➡️ Scraping stranica {page}...")
        html = get_page(page)
        if not html:
            break
        ads = parse_page(html)
        if not ads:
            print("❌ Nema više oglasa.")
            break
        all_ads.extend(ads)
        time.sleep(2)  

    with open("njuskalo_stanovi.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "price", "description", "date", "link"])
        writer.writeheader()
        writer.writerows(all_ads)

    print(f"✅ Gotovo! Spremljeno {len(all_ads)} oglasa u 'njuskalo_stanovi.csv'.")

if __name__ == "__main__":
    main()
