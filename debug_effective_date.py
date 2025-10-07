#!/usr/bin/env python3
"""
Test script to debug effective date extraction
"""
import requests
from bs4 import BeautifulSoup

def debug_effective_date():
    url = "https://www.eppo.go.th/epposite/templates/eppo_v15_mixed/eppo_oil/eppo_oil_gen_new.php"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all price rows
    price_rows = soup.find_all(['div'], class_=['oil_price_colum_name_odd', 'oil_price_colum_name_even'])
    print(f"Found {len(price_rows)} price rows")
    
    # Look for effective date row
    for i, row in enumerate(price_rows):
        row_text = row.get_text()
        print(f"Row {i}: {row_text[:100]}...")
        
        if 'Effective date' in row_text or 'มีผลบังคับใช้' in row_text:
            print(f"Found effective date row at index {i}")
            price_columns = row.find_all('div', class_='oil_price_colum')
            print(f"Number of price columns: {len(price_columns)}")
            
            for j, col in enumerate(price_columns[:3]):  # Check first 3 columns
                col_text = col.get_text().strip()
                print(f"  Column {j}: '{col_text}'")
            
            if price_columns:
                effective_text = price_columns[0].get_text().strip()
                print(f"Extracted effective date: '{effective_text}'")
            break

if __name__ == "__main__":
    debug_effective_date()