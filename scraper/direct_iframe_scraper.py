#!/usr/bin/env python3
"""
Direct iframe scraper for EPPO oil prices
เข้าไปยัง iframe โดยตรงเพื่อดึงข้อมูลราคาน้ำมัน
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import logging
from datetime import datetime
import time
import re
import os
from typing import Dict, Optional

# Import realtime data manager
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))
from scraper.realtime_data_manager import RealtimeDataManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DirectIframeScraper:
    def __init__(self):
        # Direct iframe URL
        self.iframe_url = "https://www.eppo.go.th/epposite/templates/eppo_v15_mixed/eppo_oil/eppo_oil_gen_new.php"
        self.driver = None
        
        # Initialize realtime data manager
        self.realtime_manager = RealtimeDataManager()

    def setup_driver(self):
        """ตั้งค่า Chrome WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome WebDriver initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            return False

    def scrape_iframe_directly(self) -> Optional[Dict]:
        """ดึงข้อมูลจาก iframe โดยตรง"""
        try:
            if not self.setup_driver():
                return None
                
            logger.info("Accessing iframe directly...")
            
            # Navigate directly to iframe
            self.driver.get(self.iframe_url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Get page source
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Save for debugging
            with open('direct_iframe.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            logger.info("Direct iframe content saved to direct_iframe.html")
            
            # Parse the oil price data
            return self.extract_oil_prices(soup)
            
        except Exception as e:
            logger.error(f"Error scraping iframe directly: {e}")
            return None
            
        finally:
            if self.driver:
                self.driver.quit()

    def extract_oil_prices(self, soup: BeautifulSoup) -> Optional[Dict]:
        """แยกข้อมูลราคาน้ำมันจาก HTML"""
        try:
            # Look for div_oil_price class
            oil_price_div = soup.find('div', class_='div_oil_price')
            if oil_price_div:
                logger.info("Found div_oil_price container")
                return self.parse_oil_price_structure(oil_price_div)
            
            # Alternative: look for any structure with oil prices
            page_text = soup.get_text()
            logger.info(f"Page text length: {len(page_text)}")
            logger.info(f"Page text preview: {page_text[:200]}...")
            
            # Look for price patterns
            price_pattern = re.compile(r'\b\d{2}\.\d{2}\b')
            prices = price_pattern.findall(page_text)
            logger.info(f"Found potential prices: {prices[:10]}")
            
            if prices and len(prices) >= 2:
                # Extract date from page
                current_date = datetime.now().date()
                
                # Try to find date in page
                date_patterns = [
                    r'Oil price (\d{1,2} \w+ \d{4})',
                    r'(\d{1,2}/\d{1,2}/\d{4})',
                    r'(\d{1,2}-\d{1,2}-\d{4})'
                ]
                
                for pattern in date_patterns:
                    date_match = re.search(pattern, page_text)
                    if date_match:
                        try:
                            date_str = date_match.group(1)
                            if 'Oct' in date_str or 'ตุลาคม' in date_str:
                                current_date = datetime.strptime(date_str, "%d %b %Y").date()
                            break
                        except:
                            continue
                
                return {
                    'date': current_date,
                    'price_ptt': float(prices[0]) if prices[0] else None,
                    'price_shell': float(prices[1]) if len(prices) > 1 and prices[1] else None,
                    'effective_date': None
                }
            
            logger.error("Could not extract price data")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting oil prices: {e}")
            return None

    def parse_oil_price_structure(self, oil_price_div) -> Optional[Dict]:
        """แยกข้อมูลจากโครงสร้าง div_oil_price"""
        try:
            # Extract date from header
            date_header = oil_price_div.find('div', string=re.compile(r'Oil price.*\d+.*\w+.*\d+'))
            current_date = datetime.now().date()
            
            if date_header:
                date_text = date_header.get_text()
                logger.info(f"Found date header: {date_text}")
                date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', date_text)
                if date_match:
                    try:
                        date_str = date_match.group(1)
                        current_date = datetime.strptime(date_str, "%d %b %Y").date()
                        logger.info(f"Parsed date: {current_date}")
                    except Exception as e:
                        logger.warning(f"Could not parse date: {e}")
            
            # Find gasohol rows
            gasohol_data = {'date': current_date}
            
            # Look for rows with oil_price_colum_name class
            price_rows = oil_price_div.find_all('div', class_=['oil_price_colum_name_odd', 'oil_price_colum_name_even'])
            logger.info(f"Found {len(price_rows)} price rows")
            
            for i, row in enumerate(price_rows):
                logger.info(f"Processing row {i+1}")
                
                # Look for gasohol 95 indicator
                img_tags = row.find_all('img')
                for img in img_tags:
                    img_src = img.get('src', '')
                    logger.info(f"Found image: {img_src}")
                    
                    if 'oil_name2.png' in img_src:
                        logger.info("Found Gasohol 95 row")
                        
                        # Extract price columns
                        price_columns = row.find_all('div', class_='oil_price_colum')
                        logger.info(f"Found {len(price_columns)} price columns")
                        
                        if len(price_columns) >= 2:
                            ptt_text = price_columns[0].get_text().strip()
                            shell_text = price_columns[1].get_text().strip()
                            
                            logger.info(f"PTT text: '{ptt_text}', Shell text: '{shell_text}'")
                            
                            try:
                                gasohol_data['price_ptt'] = float(ptt_text) if ptt_text != '-' else None
                            except:
                                gasohol_data['price_ptt'] = None
                                
                            try:
                                gasohol_data['price_shell'] = float(shell_text) if shell_text != '-' else None
                            except:
                                gasohol_data['price_shell'] = None
                            
                            logger.info(f"Extracted - PTT: {gasohol_data['price_ptt']}, Shell: {gasohol_data['price_shell']}")
                            
                            # Look for effective date
                            effective_rows = oil_price_div.find_all('div', class_=['oil_price_colum_name_odd', 'oil_price_colum_name_even'])
                            for eff_row in effective_rows:
                                if 'Effective date' in eff_row.get_text() or 'มีผลบังคับใช้' in eff_row.get_text():
                                    eff_columns = eff_row.find_all('div', class_='oil_price_colum')
                                    if eff_columns:
                                        gasohol_data['effective_date'] = eff_columns[0].get_text().strip()
                                        logger.info(f"Found effective date: {gasohol_data['effective_date']}")
                                    break
                            
                            return gasohol_data
            
            logger.warning("Could not find Gasohol 95 data in structured format")
            return gasohol_data if 'price_ptt' in gasohol_data or 'price_shell' in gasohol_data else None
            
        except Exception as e:
            logger.error(f"Error parsing oil price structure: {e}")
            return None

    def update_csv_file(self, new_data: Dict, csv_path: str = None) -> bool:
        """อัปเดตไฟล์ CSV ด้วยข้อมูลใหม่"""
        try:
            if not csv_path:
                csv_path = "e:\\year4_1\\T.Boat\\programs\\perfect\\data\\only_2_stations.csv"
            
            # Read existing CSV
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date']).dt.date
            else:
                # Create new DataFrame if file doesn't exist
                df = pd.DataFrame(columns=['Date', 'price_PTT', 'price_Shell', 'effective_date'])
            
            # Check if date already exists
            date_exists = False
            if not df.empty and 'Date' in df.columns:
                date_exists = df['Date'].eq(new_data['date']).any()
            
            if date_exists:
                # Update existing row
                mask = df['Date'] == new_data['date']
                df.loc[mask, 'price_PTT'] = new_data['price_ptt']
                df.loc[mask, 'price_Shell'] = new_data['price_shell'] 
                df.loc[mask, 'effective_date'] = new_data.get('effective_date')
                logger.info(f"Updated CSV row for {new_data['date']}")
            else:
                # Add new row
                new_row = {
                    'Date': new_data['date'],
                    'price_PTT': new_data['price_ptt'],
                    'price_Shell': new_data['price_shell'],
                    'effective_date': new_data.get('effective_date')
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                logger.info(f"Added new CSV row for {new_data['date']}")
            
            # Sort by date and save
            if not df.empty:
                df = df.sort_values('Date')
                df.to_csv(csv_path, index=False)
                logger.info(f"CSV file updated successfully: {csv_path}")
                
                # Also update realtime data file
                self.realtime_manager.add_realtime_data(
                    new_data['date'],
                    price_PTT=new_data['price_ptt'],
                    price_Shell=new_data['price_shell'],
                    effective_date=new_data.get('effective_date')
                )
                logger.info("Updated realtime data file")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating CSV file: {e}")
            return False

    def run_scraping(self) -> bool:
        """รันกระบวนการ scraping"""
        try:
            logger.info("=== Starting Direct Iframe Scraping ===")
            
            # Scrape data
            scraped_data = self.scrape_iframe_directly()
            if not scraped_data:
                logger.error("Failed to scrape data")
                return False
            
            logger.info(f"Scraped data: {scraped_data}")
            
            # Update CSV file
            if not self.update_csv_file(scraped_data):
                logger.error("Failed to update CSV file")
                return False
            
            logger.info("=== Scraping completed successfully ===")
            return True
            
        except Exception as e:
            logger.error(f"Error in run_scraping: {e}")
            return False

def main():
    """Main function for testing"""
    scraper = DirectIframeScraper()
    success = scraper.run_scraping()
    
    if success:
        print("✅ Direct iframe scraping completed successfully!")
    else:
        print("❌ Direct iframe scraping failed!")
        exit(1)

if __name__ == "__main__":
    main()