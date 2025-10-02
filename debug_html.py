#!/usr/bin/env python3
"""
Debug script to examine EPPO website HTML structure
"""

import requests
from bs4 import BeautifulSoup
import re

def debug_eppo_website():
    """ตรวจสอบโครงสร้าง HTML ของเว็บ EPPO"""
    
    url = "https://www.eppo.go.th/epposite/index.php/th/petroleum/price/oil-price"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print("Fetching EPPO website...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print(f"Response status: {response.status_code}")
        print(f"Content length: {len(response.content)}")
        print(f"Title: {soup.title.get_text() if soup.title else 'No title'}")
        
        # Look for any div with oil-related content
        print("\n=== Looking for oil-related divs ===")
        oil_divs = []
        for div in soup.find_all('div'):
            if div.get('class'):
                classes = div.get('class')
                if any('oil' in cls.lower() for cls in classes):
                    oil_divs.append(div)
                    print(f"Found oil div with classes: {classes}")
        
        if not oil_divs:
            print("No divs with 'oil' in class name found")
        
        # Look for price-related content
        print("\n=== Looking for price-related content ===")
        price_text = soup.get_text()
        if "ราคา" in price_text or "price" in price_text.lower():
            print("Found price-related text in page")
        else:
            print("No price-related text found")
            
        # Look for any divs containing numbers that could be prices
        print("\n=== Looking for potential price divs ===")
        price_pattern = re.compile(r'\d+\.\d+')
        potential_price_divs = []
        
        for div in soup.find_all('div'):
            text = div.get_text().strip()
            if price_pattern.search(text):
                potential_price_divs.append(div)
                
        print(f"Found {len(potential_price_divs)} divs with decimal numbers")
        
        # Show first few potential price divs
        for i, div in enumerate(potential_price_divs[:5]):
            print(f"Price div {i+1}: {div.get_text().strip()[:100]}...")
            if div.get('class'):
                print(f"  Classes: {div.get('class')}")
        
        # Look for today's date
        print("\n=== Looking for date information ===")
        today_patterns = [
            r'2\s+(Oct|เมษายน)\s+2025',
            r'2\s+ตุลาคม\s+2568',
            r'Oil\s+price\s+\d+\s+\w+\s+\d+'
        ]
        
        page_text = soup.get_text()
        for pattern in today_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                print(f"Found date pattern: {matches}")
        
        # Save HTML for manual inspection
        with open('eppo_debug.html', 'w', encoding='utf-8') as f:
            f.write(str(soup.prettify()))
        print("\nHTML saved to eppo_debug.html for manual inspection")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_eppo_website()