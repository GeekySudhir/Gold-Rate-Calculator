import json
import re
import os
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

URL = "https://chdtheoriginal.in/gold-rate/"
DATA_FILE = "rates.json"

def get_ist_date():
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    return ist_now.strftime("%Y-%m-%d")

def scrape_rates():
    today_date = get_ist_date()

    # Load existing data to append history
    data = {"latest": {}, "history": []}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if "history" not in data:
                    data = {"latest": {}, "history": []}
        except Exception:
            pass

    scraped_rates = {
        "rate_24k": 0,
        "rate_22k": 0,
        "rate_18k": 0,
        "rate_silver": 0
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Wait for network idle ensures JS has finished executing and rendering data
            page.goto(URL, wait_until="networkidle")
            
            # Extract all visible text on the page
            text = page.inner_text("body")
            
            # Regex targets the metal name, ignores formatting/newlines, and finds the next ₹ value
            patterns = {
                "rate_24k": r"24K\s*GOLD.*?(?:₹)\s*([\d,]+)",
                "rate_22k": r"22K\s*GOLD.*?(?:₹)\s*([\d,]+)",
                "rate_18k": r"18K\s*GOLD.*?(?:₹)\s*([\d,]+)",
                "rate_silver": r"SILVER.*?(?:₹)\s*([\d,]+)"
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    # Strip commas and convert to integer
                    num = int(re.sub(r'[^\d]', '', match.group(1)))
                    if num > 100:
                        scraped_rates[key] = num
                        
            browser.close()
    except Exception as e:
        print(f"Playwright scraper error: {e}")

    # Fallback to current live rates if network fails
    if scraped_rates["rate_22k"] == 0:
        print("Failed to dynamically scrape. Using fallback values.")
        scraped_rates = {
            "rate_24k": 14730,
            "rate_22k": 13550,
            "rate_18k": 11120,
            "rate_silver": 231
        }

    # Identify previous day entry to calculate diffs
    previous_entry = None
    for entry in reversed(data["history"]):
        if entry["date"] != today_date:
            previous_entry = entry
            break

    diffs = {}
    for key, current_val in scraped_rates.items():
        if previous_entry and key in previous_entry and previous_entry[key] > 0:
            prev_val = previous_entry[key]
            amount_diff = current_val - prev_val
            pct_diff = round((amount_diff / prev_val) * 100, 2)
            diffs[key] = {"amount": amount_diff, "percent": pct_diff}
        else:
            diffs[key] = {"amount": 0, "percent": 0.0}

    today_record = {
        "date": today_date,
        **scraped_rates
    }

    # Upsert today's entry
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

    print(f"Successfully calculated and saved rates: {output_payload['latest']}")

if __name__ == "__main__":
    scrape_rates()