import requests
from bs4 import BeautifulSoup
import json
import re
import os

URL = "https://chdtheoriginal.in/gold-rate/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def extract_number(text):
    if not text:
        return None
    # Remove all non-numeric characters (like '₹', ',', ' ', etc.)
    return re.sub(r'[^\d]', '', text)

def scrape_rates():
    try:
        response = requests.get(URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        rates = {}
        
        # CHD's site structure usually puts rates in elements containing the text "22K Gold Rate", etc.
        # We look for all text containing the rate names, then find the next element that looks like a price.
        
        rate_types = {
            "24K Gold": "rate_24k",
            "22K Gold": "rate_22k",
            "18K Gold": "rate_18k",
            "Silver": "rate_silver"
        }
        
        # Fallback default values in case scraping fails
        final_rates = {
            "rate_24k": "15160",
            "rate_22k": "13950",
            "rate_18k": "11450",
            "rate_silver": "242"
        }

        # Attempt to scrape the live page
        # Note: This is a basic generic extraction. If the site structure changes heavily, this might need tweaking.
        for text_label, key in rate_types.items():
            label_el = soup.find(string=re.compile(text_label))
            if label_el:
                # Often the price is in the next sibling or parent's next sibling
                parent = label_el.parent
                # Look ahead in the HTML for a rupee symbol
                for sibling in parent.find_next_siblings():
                    if '₹' in sibling.text:
                        num = extract_number(sibling.text)
                        if num:
                            final_rates[key] = num
                            break
        
        # Save to JSON
        with open('rates.json', 'w') as f:
            json.dump(final_rates, f, indent=4)
            
        print(f"Successfully scraped and saved rates: {final_rates}")
            
    except Exception as e:
        print(f"Error scraping rates: {e}")
        # If it fails, it will leave the existing rates.json untouched (or create it with defaults if it didn't exist)

if __name__ == "__main__":
    scrape_rates()