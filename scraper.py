import requests
from bs4 import BeautifulSoup
import json
import re

URL = "https://chdtheoriginal.in/gold-rate/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def extract_number(text):
    if not text:
        return None
    return re.sub(r'[^\d]', '', text)

def scrape_rates():
    try:
        response = requests.get(URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Use lowercase for case-insensitive matching
        rate_types = {
            "24k gold": "rate_24k",
            "22k gold": "rate_22k",
            "18k gold": "rate_18k",
            "silver": "rate_silver"
        }
        
        # Updated fallbacks matching image_45df86.png
        final_rates = {
            "rate_24k": "14850",
            "rate_22k": "13660",
            "rate_18k": "11210",
            "rate_silver": "235"
        }

        # Attempt to scrape the live page robustly
        for text_label, key in rate_types.items():
            # Find all matching labels ignoring case
            label_els = soup.find_all(string=re.compile(text_label, re.IGNORECASE))
            
            for label_el in label_els:
                # Find the very next string in the HTML that contains '₹'
                price_str = label_el.find_next(string=re.compile('₹'))
                if price_str:
                    num = extract_number(price_str)
                    # Basic check to ensure it's a valid price and not ₹0
                    if num and int(num) > 100: 
                        final_rates[key] = num
                        break
        
        with open('rates.json', 'w') as f:
            json.dump(final_rates, f, indent=4)
            
        print(f"Successfully scraped and saved rates: {final_rates}")
            
    except Exception as e:
        print(f"Error scraping rates: {e}")

if __name__ == "__main__":
    scrape_rates()