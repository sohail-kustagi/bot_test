from bs4 import BeautifulSoup
import pandas as pd
import requests

def get_article(data):
    return dict(
        headline=data.get_text(),
        link='https://www.bloomberg.com' + data['href']
    )

def bloomberg_com():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0"
    }

    resp = requests.get("https://www.bloomberg.com/fx-center", headers=headers)
    soup = BeautifulSoup(resp.content, 'html.parser')

    print("[DEBUG] Fetching Bloomberg headlines...")
    print(f"[DEBUG] Response status code: {resp.status_code}")
    print(f"[DEBUG] Response content: {resp.content[:500]}...")  # Log the first 500 characters of the response

    all_links = []

    # Updated selectors based on the Bloomberg FX Center page structure
    headline_elements = soup.select("a[data-tracker-event='headline']")

    for element in headline_elements:
        headline_text = element.get_text(strip=True)
        headline_link = element['href'] if element.has_attr('href') else None

        if headline_text and headline_link:
            all_links.append({
                'headline': headline_text,
                'link': headline_link if headline_link.startswith("http") else f"https://www.bloomberg.com{headline_link}"
            })

    print(f"[DEBUG] Total articles fetched: {len(all_links)}")
    return all_links
