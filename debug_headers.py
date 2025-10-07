#!/usr/bin/env python3
"""
Debug script to identify oil station column headers
"""

import requests
from bs4 import BeautifulSoup
import re

def debug_station_headers():
    """Debug the EPPO website station header structure"""
    base_url = "https://www.eppo.go.th/epposite/templates/eppo_v15_mixed/eppo_oil/eppo_oil_gen_new.php"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print("Fetching EPPO website...")
        response = requests.get(base_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the oil price container
        oil_price_div = soup.find('div', class_='div_oil_price')
        if not oil_price_div:
            print("ERROR: Could not find oil price container")
            return
        
        print("Found oil price container")
        
        # Look for the header row with station logos - try different selectors
        header_divs = oil_price_div.find_all('div', class_='oil_price_colum_name_header')
        print(f"Found {len(header_divs)} header divs with class 'oil_price_colum_name_header'")
        
        # Also try to find any div that contains oil station images
        all_divs = oil_price_div.find_all('div')
        print(f"Total divs in oil_price_div: {len(all_divs)}")
        
        # Look for divs containing oil station images
        station_divs = []
        for div in all_divs:
            imgs = div.find_all('img')
            for img in imgs:
                img_src = img.get('src', '')
                if any(station in img_src for station in ['oil_1.png', 'oil_2.png', 'oil_3.png', 'oil_4.png', 'oil_5.png']):
                    if div not in station_divs:
                        station_divs.append(div)
                        
        print(f"Found {len(station_divs)} divs containing station images")
        
        # Analyze station divs
        for div_idx, div in enumerate(station_divs):
            print(f"\n=== STATION DIV {div_idx} ===")
            print(f"Class: {div.get('class', [])}")
            
            # Check if this is a multi-column header
            columns = div.find_all('div', class_='oil_price_colum')
            if len(columns) > 1:
                print(f"Multi-column header with {len(columns)} columns:")
                for col_idx, column in enumerate(columns):
                    col_imgs = column.find_all('img')
                    for img in col_imgs:
                        img_src = img.get('src', '')
                        print(f"  Column {col_idx}: {img_src}")
                        
                        # Identify stations
                        if 'oil_1.png' in img_src:
                            print(f"    --> PTT (Column {col_idx})")
                        elif 'oil_2.png' in img_src:
                            print(f"    --> ESSO (Column {col_idx})")
                        elif 'oil_3.png' in img_src:
                            print(f"    --> SHELL (Column {col_idx})")
                        elif 'oil_4.png' in img_src:
                            print(f"    --> CHEVRON (Column {col_idx})")
                        elif 'oil_5.png' in img_src:
                            print(f"    --> BANGCHAK (Column {col_idx})")
            else:
                # Single image div
                imgs = div.find_all('img')
                for img in imgs:
                    img_src = img.get('src', '')
                    print(f"Single station image: {img_src}")
        
        # If no specific header found, just analyze the structure
        if not header_divs and not station_divs:
            print("\nNo headers found, analyzing overall structure...")
            
        for header_idx, header_div in enumerate(header_divs):
            print(f"\n=== HEADER {header_idx} ===")
            
            # Find all columns in this header
            columns = header_div.find_all('div', class_='oil_price_colum')
            print(f"Found {len(columns)} columns in header")
            
            for col_idx, column in enumerate(columns):
                col_text = column.get_text().strip()
                print(f"\nColumn {col_idx}: '{col_text}'")
                
                # Look for images in this column
                col_imgs = column.find_all('img')
                for img in col_imgs:
                    img_src = img.get('src', '')
                    print(f"  Image: {img_src}")
                    
                    # Identify stations by their image files
                    if 'oil_1.png' in img_src:
                        print(f"  --> PTT (Column {col_idx})")
                    elif 'oil_2.png' in img_src:
                        print(f"  --> ESSO (Column {col_idx})")
                    elif 'oil_3.png' in img_src:
                        print(f"  --> SHELL (Column {col_idx})")
                    elif 'oil_4.png' in img_src:
                        print(f"  --> CHEVRON (Column {col_idx})")
                    elif 'oil_5.png' in img_src:
                        print(f"  --> BANGCHAK (Column {col_idx})")
                    elif 'oil_6.png' in img_src:
                        print(f"  --> IRPC (Column {col_idx})")
                    elif 'oil_7.png' in img_src:
                        print(f"  --> SUSCO (Column {col_idx})")
                    elif 'oil_8.png' in img_src:
                        print(f"  --> PURE (Column {col_idx})")
                    elif 'oil_9.png' in img_src:
                        print(f"  --> KASET (Column {col_idx})")
                    elif 'oil_10.png' in img_src:
                        print(f"  --> PT (Column {col_idx})")
                    else:
                        print(f"  --> UNKNOWN STATION: {img_src}")
    
    except Exception as e:
        print(f"Error debugging station headers: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_station_headers()