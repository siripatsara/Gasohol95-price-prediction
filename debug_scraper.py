#!/usr/bin/env python3
"""
Debug script to test EPPO oil price column parsing
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

def debug_eppo_columns():
    """Debug the EPPO website column structure"""
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
        
        # Find all price rows
        price_rows = oil_price_div.find_all('div', class_=re.compile(r'oil_price_colum_name_(odd|even)'))
        print(f"Found {len(price_rows)} price rows")
        
        # Analyze each row
        for row_idx, row in enumerate(price_rows):
            print(f"\n=== ROW {row_idx} ===")
            
            # Check for images to identify the fuel type
            img_tag = row.find('img')
            if img_tag:
                img_src = img_tag.get('src', '')
                print(f"Image: {img_src}")
                
                # Check for Gasohol 95 (oil_name2.png)
                if 'oil_name2.png' in img_src:
                    print("*** This is GASOHOL 95 row ***")
                    
                    # Get all price columns
                    price_columns = row.find_all('div', class_='oil_price_colum')
                    print(f"Found {len(price_columns)} price columns")
                    
                    # Analyze each column
                    for col_idx, column in enumerate(price_columns):
                        col_text = column.get_text().strip()
                        print(f"  Column {col_idx}: '{col_text}'")
                        
                        # Look for images in this column to identify the station
                        col_imgs = column.find_all('img')
                        for col_img in col_imgs:
                            col_img_src = col_img.get('src', '')
                            print(f"    Column image: {col_img_src}")
                            
                            # Identify specific stations
                            if 'oil_1.png' in col_img_src:
                                print(f"    --> PTT STATION: {col_text}")
                            elif 'oil_3.png' in col_img_src:
                                print(f"    --> SHELL STATION: {col_text}")
                            elif 'oil_2.png' in col_img_src:
                                print(f"    --> ESSO STATION: {col_text}")
                            elif 'oil_5.png' in col_img_src:
                                print(f"    --> BANGCHAK STATION: {col_text}")
                        
                        # If no image, this might be a price cell
                        if not col_imgs and col_text and col_text != '-':
                            try:
                                price_val = float(col_text)
                                print(f"    --> PRICE: {price_val}")
                            except ValueError:
                                print(f"    --> TEXT: {col_text}")
                
            else:
                # No image - might be effective date or other info
                row_text = row.get_text().strip()
                if 'Effective date' in row_text or 'มีผลบังคับใช้' in row_text:
                    print("*** This is EFFECTIVE DATE row ***")
                    price_columns = row.find_all('div', class_='oil_price_colum')
                    for col_idx, column in enumerate(price_columns):
                        col_text = column.get_text().strip()
                        if col_text:
                            print(f"  Column {col_idx}: '{col_text}'")
                else:
                    print(f"Other row: {row_text[:100]}...")
    
    except Exception as e:
        print(f"Error debugging EPPO columns: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_eppo_columns()