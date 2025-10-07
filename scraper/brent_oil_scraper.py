#!/usr/bin/env python3
"""
Brent Oil Price Scraper from FRED (Federal Reserve Economic Data)
ดึงข้อมูลราคาน้ำมันดิบเบรนท์จาก https://fred.stlouisfed.org/series/DCOILBRENTEU
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import logging
from datetime import datetime, timedelta
import time
import re
import os
from typing import Dict, List, Optional, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BrentOilScraper:
    def __init__(self):
        self.fred_url = "https://fred.stlouisfed.org/series/DCOILBRENTEU"
        self.driver = None

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

    def scrape_brent_prices(self) -> Optional[Dict]:
        """ดึงข้อมูลราคาน้ำมันดิบเบรนท์จาก FRED"""
        try:
            if not self.setup_driver():
                return None
                
            logger.info("Accessing FRED Brent Oil page...")
            
            # Navigate to FRED page
            self.driver.get(self.fred_url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Get page source
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Save for debugging
            with open('fred_brent_debug.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            logger.info("FRED page content saved to fred_brent_debug.html")
            
            # Extract latest price and historical data
            latest_data = self.extract_latest_price(soup)
            historical_data = self.extract_recent_observations(soup)
            
            return {
                'latest': latest_data,
                'historical': historical_data
            }
            
        except Exception as e:
            logger.error(f"Error scraping Brent prices: {e}")
            return None
            
        finally:
            if self.driver:
                self.driver.quit()

    def extract_latest_price(self, soup: BeautifulSoup) -> Optional[Dict]:
        """แยกข้อมูลราคาล่าสุด"""
        try:
            # Look for the latest observation
            meta_col = soup.find('div', class_='meta-col')
            if not meta_col:
                logger.error("Could not find meta-col div")
                return None
            
            # Extract date and price
            date_span = meta_col.find('span', class_='series-meta-value')
            price_span = meta_col.find('span', class_='series-meta-observation-value')
            
            if date_span and price_span:
                date_text = date_span.get_text().strip().replace(':', '')
                price_text = price_span.get_text().strip()
                
                logger.info(f"Found latest data - Date: {date_text}, Price: {price_text}")
                
                # Parse date
                try:
                    latest_date = datetime.strptime(date_text, "%Y-%m-%d").date()
                except:
                    logger.error(f"Could not parse date: {date_text}")
                    return None
                
                # Parse price
                try:
                    latest_price = float(price_text)
                except:
                    logger.error(f"Could not parse price: {price_text}")
                    return None
                
                return {
                    'date': latest_date,
                    'price': latest_price
                }
            
            logger.error("Could not find date or price elements")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting latest price: {e}")
            return None

    def extract_recent_observations(self, soup: BeautifulSoup) -> List[Dict]:
        """แยกข้อมูลย้อนหลัง 5-10 วัน"""
        try:
            historical_data = []
            
            # Look for the recent observations table
            recent_table = soup.find('table', id='recent-obs')
            if not recent_table:
                logger.warning("Could not find recent observations table")
                return historical_data
            
            rows = recent_table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    date_cell = cells[0]
                    price_cell = cells[1]
                    
                    # Extract and clean data
                    date_text = date_cell.get_text().strip().replace(':', '').replace('\xa0', '')
                    price_text = price_cell.get_text().strip()
                    
                    # Skip if not valid data
                    if not date_text or not price_text or 'View All' in price_text:
                        continue
                    
                    try:
                        obs_date = datetime.strptime(date_text, "%Y-%m-%d").date()
                        obs_price = float(price_text)
                        
                        historical_data.append({
                            'date': obs_date,
                            'price': obs_price
                        })
                        
                        logger.info(f"Historical data: {obs_date} -> {obs_price}")
                        
                    except Exception as e:
                        logger.debug(f"Could not parse row data: {date_text}, {price_text} - {e}")
                        continue
            
            return historical_data
            
        except Exception as e:
            logger.error(f"Error extracting recent observations: {e}")
            return []

    def get_brent_price_for_date(self, target_date: datetime.date, scraped_data: Dict) -> Optional[float]:
        """หาราคาน้ำมันดิบสำหรับวันที่ต้องการ"""
        try:
            latest_data = scraped_data.get('latest')
            historical_data = scraped_data.get('historical', [])
            
            if not latest_data:
                logger.error("No latest data available")
                return None
            
            # Check if target date matches latest data
            if latest_data['date'] == target_date:
                logger.info(f"Found exact match for {target_date}: {latest_data['price']}")
                return latest_data['price']
            
            # Check historical data
            for hist_data in historical_data:
                if hist_data['date'] == target_date:
                    logger.info(f"Found historical match for {target_date}: {hist_data['price']}")
                    return hist_data['price']
            
            # Forward fill with latest available data
            latest_price = latest_data['price']
            logger.info(f"Forward filling {target_date} with latest price: {latest_price}")
            return latest_price
            
        except Exception as e:
            logger.error(f"Error getting Brent price for date: {e}")
            return None

    def update_csv_with_brent_prices(self, csv_path: str = None) -> bool:
        """อัปเดตไฟล์ CSV ด้วยราคาน้ำมันดิบเบรนท์"""
        try:
            if not csv_path:
                csv_path = "e:\\year4_1\\T.Boat\\programs\\perfect\\data\\only_2_stations.csv"
            
            if not os.path.exists(csv_path):
                logger.error(f"CSV file not found: {csv_path}")
                return False
            
            # Read CSV
            df = pd.read_csv(csv_path)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            
            # Scrape Brent data
            logger.info("Scraping Brent oil prices...")
            scraped_data = self.scrape_brent_prices()
            if not scraped_data:
                logger.error("Failed to scrape Brent data")
                return False
            
            # Update missing Brent prices
            updated_rows = 0
            for index, row in df.iterrows():
                # Check if Price_Brent is missing or NaN
                if pd.isna(row.get('Price_Brent')):
                    brent_price = self.get_brent_price_for_date(row['Date'], scraped_data)
                    if brent_price:
                        df.at[index, 'Price_Brent'] = brent_price
                        updated_rows += 1
                        logger.info(f"Updated {row['Date']} with Brent price: {brent_price}")
            
            # Check for potential updates to existing data
            latest_data = scraped_data.get('latest')
            if latest_data:
                # Look for rows that might need updating based on new data
                for hist_data in scraped_data.get('historical', []):
                    mask = df['Date'] == hist_data['date']
                    if mask.any():
                        current_price = df.loc[mask, 'Price_Brent'].iloc[0]
                        if pd.notna(current_price) and abs(current_price - hist_data['price']) > 0.01:
                            logger.info(f"Updating {hist_data['date']}: {current_price} -> {hist_data['price']}")
                            df.loc[mask, 'Price_Brent'] = hist_data['price']
                            updated_rows += 1
            
            # Save updated CSV
            df.to_csv(csv_path, index=False)
            logger.info(f"Updated {updated_rows} rows with Brent prices")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating CSV with Brent prices: {e}")
            return False

    def run(self) -> bool:
        """รันกระบวนการ scraping Brent oil prices (สำหรับ Smart Scraper)"""
        return self.run_brent_scraping()
    
    def run_brent_scraping(self) -> bool:
        """รันกระบวนการ scraping Brent oil prices"""
        try:
            logger.info("=== Starting Brent Oil Price Scraping ===")
            
            success = self.update_csv_with_brent_prices()
            
            if success:
                logger.info("=== Brent Oil Price Scraping completed successfully ===")
            else:
                logger.error("=== Brent Oil Price Scraping failed ===")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in run_brent_scraping: {e}")
            return False

def main():
    """Main function for testing"""
    scraper = BrentOilScraper()
    success = scraper.run_brent_scraping()
    
    if success:
        print("✅ Brent oil scraping completed successfully!")
    else:
        print("❌ Brent oil scraping failed!")
        exit(1)

if __name__ == "__main__":
    main()