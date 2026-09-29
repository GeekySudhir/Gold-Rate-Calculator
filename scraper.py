import requests
from bs4 import BeautifulSoup
import json
import re
import os
from datetime import datetime, timezone, timedelta

URL = "https://chdtheoriginal.in/gold-rate/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
DATA_FILE = "rates.json"

def extract_number(text):
    if not text:
        return None
    cleaned = re.sub(r'[^\d]', '', text)
    return int(cleaned) if cleaned else None

def get_ist_date():
    # UTC + 5:30 for Indian Standard Time
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    return ist_now.strftime("%Y-%m-%d")

def scrape_rates():
    today_date = get_ist_date()

    # Load existing data if available
    data = {"latest": {}, "history": []}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if "history" not in data:
                    data = {"latest": {}, "history": []}
        except Exception as e:
            print(f"Warning: Could not read existing {DATA_FILE}: {e}")

    # Fallback rates in case scraping fails
    scraped_rates = {
        "rate_24k": 14850,
        "rate_22k": 13660,
        "rate_18k": 11210,
        "rate_silver": 235
    }

    try:
        response = requests.get(URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        rate_types = {
            "24k gold": "rate_24k",
            "22k gold": "rate_22k",
            "18k gold": "rate_18k",
            "silver": "rate_silver"
        }

        for text_label, key in rate_types.items():
            label_els = soup.find_all(string=re.compile(text_label, re.IGNORECASE))
            for label_el in label_els:
                price_str = label_el.find_next(string=re.compile("₹"))
                if price_str:
                    num = extract_number(price_str)
                    if num and num > 100:
                        scraped_rates[key] = num
                        break
    except Exception as e:
        print(f"Scraper error (using defaults/existing): {e}")

    # Identify previous day entry from history
    previous_entry = None
    for entry in reversed(data["history"]):
        if entry["date"] != today_date:
            previous_entry = entry
            break

    # Compute difference vs previous day
    diffs = {}
    for key, current_val in scraped_rates.items():
        if previous_entry and key in previous_entry and previous_entry[key] > 0:
            prev_val = previous_entry[key]
            amount_diff = current_val - prev_val
            pct_diff = round((amount_diff / prev_val) * 100, 2)
            diffs[key] = {
                "amount": amount_diff,
                "percent": pct_diff
            }
        else:
            diffs[key] = {
                "amount": 0,
                "percent": 0.0
            }

    today_record = {
        "date": today_date,
        **scraped_rates
    }

    # Upsert today's entry into history
    history = [h for h in data["history"] if h.get("date") != today_date]
    history.append(today_record)
    history.sort(key=lambda x: x["date"])

    output_payload = {
        "latest": {
            "date": today_date,
            "rates": scraped_rates,
            "diff": diffs
        },
        "history": history
    }

    with open(DATA_FILE, "w") as f:
        json.dump(output_payload, f, indent=2)

    print(f"Updated {DATA_FILE} successfully for date {today_date}: {output_payload['latest']}")

if __name__ == "__main__":
    scrape_rates()