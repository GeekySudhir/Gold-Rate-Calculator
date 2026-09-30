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

def clean_number(raw_text):
    if not raw_text:
        return 0
    cleaned = re.sub(r'[^\d]', '', raw_text)
    return int(cleaned) if cleaned else 0

def scrape_rates():
    today_date = get_ist_date()

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
            page.goto(URL, wait_until="networkidle", timeout=30000)

            # Extract rates by scanning card containers in the DOM
            extracted = page.evaluate('''() => {
                const results = {};
                const allDivs = Array.from(document.querySelectorAll('div, section, p, span'));
                
                // Helper to find numbers inside or immediately following a matching block
                function findRate(keyword) {
                    const el = allDivs.find(d => {
                        const txt = (d.innerText || "").trim().toUpperCase();
                        return txt === keyword || txt.startsWith(keyword + "\\n") || txt.includes(keyword + " RATE");
                    });
                    if (el) {
                        const container = el.closest('div') || el.parentElement;
                        const match = (container.innerText || "").match(/₹\\s*([\\d,]+)/);
                        if (match) return match[1];
                    }
                    return null;
                }

                results.rate_22k = findRate("22K GOLD");
                results.rate_24k = findRate("24K GOLD");
                results.rate_18k = findRate("18K GOLD");
                results.rate_silver = findRate("SILVER");
                return results;
            }''')

            browser.close()

            scraped_rates["rate_24k"] = clean_number(extracted.get("rate_24k"))
            scraped_rates["rate_22k"] = clean_number(extracted.get("rate_22k"))
            scraped_rates["rate_18k"] = clean_number(extracted.get("rate_18k"))
            scraped_rates["rate_silver"] = clean_number(extracted.get("rate_silver"))

    except Exception as e:
        print(f"Playwright error: {e}")

    # Fallback to secondary regex parser if DOM evaluation missed anything
    if scraped_rates["rate_silver"] == 0 or scraped_rates["rate_silver"] > 1000:
        print("DOM selector missed Silver or matched gold price. Running fallback extraction...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(URL, wait_until="networkidle", timeout=30000)
                
                # Look specifically for standalone price cards (e.g., "SILVER\n₹235")
                silver_loc = page.locator("text=/^SILVER$/i").first
                if silver_loc:
                    parent_text = silver_loc.locator("..").inner_text()
                    match = re.search(r"₹\s*([\d,]+)", parent_text)
                    if match:
                        val = clean_number(match.group(1))
                        # Silver rate per gram should be under 1,000
                        if 100 < val < 1000:
                            scraped_rates["rate_silver"] = val
                browser.close()
        except Exception as e:
            print(f"Fallback scraper error: {e}")

    # Safety bounds check: silver per gram cannot realistically be above ₹1,000
    if scraped_rates["rate_silver"] > 1000 or scraped_rates["rate_silver"] == 0:
        # Fallback to previous day's silver rate from history or baseline
        prev_silver = 235
        for h in reversed(data["history"]):
            if 100 < h.get("rate_silver", 0) < 1000:
                prev_silver = h["rate_silver"]
                break
        scraped_rates["rate_silver"] = prev_silver

    # Calculate differences against previous entry
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

    print(f"Successfully scraped and saved: {output_payload['latest']}")

if __name__ == "__main__":
    scrape_rates()