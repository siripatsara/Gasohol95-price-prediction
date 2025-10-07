#!/usr/bin/env python3
"""
BOT USD/THB Exchange Rate Scraper
ดึงข้อมูลอัตราแลกเปลี่ยน USD/THB จาก Bank of Thailand
https://www.bot.or.th/en/statistics/exchange-rate.html
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import logging
from datetime import datetime, timedelta
import time
import re
import os
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BOTUSDTHBScraper:
    def __init__(self):
        self.base_url = "https://www.bot.or.th/en/statistics/exchange-rate.html"
        self.driver = None

    def setup_driver(self):
        """ตั้งค่า Chrome WebDriver with improved container compatibility"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # Try different approaches for Chrome WebDriver setup
            try:
                # Approach 1: Use ChromeDriverManager (most reliable for local development)
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("Chrome WebDriver initialized with ChromeDriverManager")
                return True
                
            except Exception as e1:
                logger.warning(f"ChromeDriverManager failed: {e1}, trying system Chrome...")
                
                # Approach 2: Try system Chrome (for container environment)
                try:
                    chrome_options.binary_location = '/usr/bin/google-chrome'
                    service = Service('/usr/bin/chromedriver') if os.path.exists('/usr/bin/chromedriver') else Service()
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    logger.info("Chrome WebDriver initialized with system Chrome")
                    return True
                    
                except Exception as e2:
                    logger.warning(f"System Chrome failed: {e2}, trying Windows Chrome...")
                    
                    # Approach 3: Try Windows Chrome locations
                    chrome_paths = [
                        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                        r'C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe'.format(os.getenv('USERNAME', ''))
                    ]
                    
                    for chrome_path in chrome_paths:
                        if os.path.exists(chrome_path):
                            try:
                                chrome_options.binary_location = chrome_path
                                service = Service(ChromeDriverManager().install())
                                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                                logger.info(f"Chrome WebDriver initialized with {chrome_path}")
                                return True
                            except Exception as e3:
                                logger.warning(f"Chrome path {chrome_path} failed: {e3}")
                                continue
                    
                    # If all approaches fail
                    logger.error("All Chrome WebDriver initialization methods failed")
                    return False
            
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            return False

    def scrape_usd_thb_rate(self) -> Optional[Dict]:
        """ดึงข้อมูลอัตราแลกเปลี่ยน USD/THB จาก BOT"""
        try:
            if not self.setup_driver():
                return None
                
            logger.info("Accessing BOT exchange rate page...")
            
            # Navigate to the page
            self.driver.get(self.base_url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Try to select USD currency
            try:
                logger.info("Looking for currency dropdown...")
                # Find and click currency dropdown
                currency_dropdown = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "dropdownCurrency"))
                )
                currency_dropdown.click()
                time.sleep(2)
                
                # Select USD
                usd_option = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'dropdown-item') and contains(text(), 'USD')]"))
                )
                usd_option.click()
                logger.info("Selected USD currency")
                time.sleep(2)
                
            except Exception as e:
                logger.warning(f"Could not select USD currency: {e}")
            
            # Try to set date range to today
            try:
                logger.info("Setting date range...")
                today = datetime.now()
                date_str = today.strftime("%d/%m/%Y")
                
                # Find date input fields
                date_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[placeholder='Select a date']")
                
                if len(date_inputs) >= 2:
                    # Set "from" date to today
                    date_inputs[0].clear()
                    date_inputs[0].send_keys(date_str)
                    
                    # Set "to" date to today
                    date_inputs[1].clear()
                    date_inputs[1].send_keys(date_str)
                    
                    logger.info(f"Set date range to {date_str}")
                    time.sleep(1)
                    
                    # Click GO button
                    go_button = self.driver.find_element(By.CSS_SELECTOR, "button.historical-btn")
                    go_button.click()
                    logger.info("Clicked GO button")
                    time.sleep(5)
                
            except Exception as e:
                logger.warning(f"Could not set date range: {e}")
            
            # Get page source and parse
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Save for debugging
            with open('bot_usdthb_debug.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            logger.info("BOT page saved to bot_usdthb_debug.html")
            
            # Parse exchange rate data
            return self.extract_exchange_rate(soup)
            
        except Exception as e:
            logger.error(f"Error scraping USD/THB rate: {e}")
            return None
            
        finally:
            if self.driver:
                self.driver.quit()

    def extract_exchange_rate(self, soup: BeautifulSoup) -> Optional[Dict]:
        """แยกข้อมูลอัตราแลกเปลี่ยนจาก HTML และคืนข้อมูลหลายวัน"""
        try:
            # Look for table data
            table = soup.find('table')
            if table:
                logger.info("Found exchange rate table")
                
                # Look for table rows
                rows = table.find_all('tr')
                logger.info(f"Found {len(rows)} table rows")
                
                exchange_data = []
                
                for row in rows[1:]:  # Skip header row
                    cells = row.find_all('td')
                    if len(cells) >= 4:  # Need at least 4 columns to access all data
                        date_text = cells[0].get_text().strip()
                        buying_sight_bill = cells[1].get_text().strip()  # Buying Rates Sight Bill ← ใช้อันนี้!
                        buying_transfer = cells[2].get_text().strip()    # Buying Rates Transfer
                        selling_rate_text = cells[3].get_text().strip()  # Average Selling Rates
                        
                        logger.info(f"Found row: {date_text} -> Buying Sight Bill: {buying_sight_bill} (Selling: {selling_rate_text})")
                        
                        # Parse date
                        try:
                            # Expected format: "02 Oct 2025" or "01 Oct 2025"
                            parsed_date = datetime.strptime(date_text, "%d %b %Y").date()
                            
                            # Parse Buying Rates Sight Bill (this is what we want!)
                            rate = float(buying_sight_bill)
                            
                            exchange_data.append({
                                'date': parsed_date,
                                'usd_thb_rate': rate,
                                'buying_sight_bill': rate,
                                'buying_transfer': float(buying_transfer),
                                'selling_rate': float(selling_rate_text),
                                'source': 'BOT'
                            })
                                
                        except ValueError as e:
                            # Try alternative date formats
                            try:
                                # Try format: "2 Oct 2025" (without leading zero)
                                parsed_date = datetime.strptime(date_text, "%d %b %Y").date()
                                rate = float(buying_sight_bill)
                                
                                exchange_data.append({
                                    'date': parsed_date,
                                    'usd_thb_rate': rate,
                                    'buying_sight_bill': rate,
                                    'source': 'BOT'
                                })
                            except Exception as e2:
                                logger.warning(f"Could not parse date '{date_text}': {e}")
                                continue
                        except Exception as e:
                            logger.warning(f"Could not parse row data: {e}")
                            continue
                
                # Return all data found, sorted by date (newest first)
                if exchange_data:
                    exchange_data.sort(key=lambda x: x['date'], reverse=True)
                    logger.info(f"Found {len(exchange_data)} exchange rate records")
                    for data in exchange_data[:5]:  # Log first 5 records
                        logger.info(f"  {data['date']}: {data['usd_thb_rate']}")
                    return {'exchange_data': exchange_data}
                    
                logger.warning("No valid exchange rate data found in table")
            
            # Alternative: look for any numeric data that might be exchange rate
            page_text = soup.get_text()
            rate_pattern = re.compile(r'32\.\d{4}')  # Pattern for THB rate (around 32.xxxx)
            rates = rate_pattern.findall(page_text)
            
            if rates:
                logger.info(f"Found potential rates: {rates}")
                # Use the first rate found as fallback
                return {
                    'exchange_data': [{
                        'date': datetime.now().date(),
                        'usd_thb_rate': float(rates[0]),
                        'source': 'BOT_fallback'
                    }]
                }
            
            logger.error("Could not extract exchange rate data")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting exchange rate: {e}")
            return None

    def get_existing_usd_thb_data(self, csv_path: str = None) -> Dict:
        """ดึงข้อมูล USD_BATH ที่มีอยู่ใน CSV"""
        try:
            if not csv_path:
                csv_path = "e:\\year4_1\\T.Boat\\programs\\perfect\\data\\only_2_stations.csv"
            
            if not os.path.exists(csv_path):
                return {}
                
            df = pd.read_csv(csv_path)
            
            if 'Date' in df.columns and 'USD_BATH' in df.columns:
                df['Date'] = pd.to_datetime(df['Date']).dt.date
                
                # สร้าง dictionary ของข้อมูลที่มีอยู่
                existing_data = {}
                for _, row in df.iterrows():
                    if pd.notna(row['USD_BATH']):
                        existing_data[row['Date']] = row['USD_BATH']
                
                logger.info(f"Found {len(existing_data)} existing USD_BATH records")
                return existing_data
                
            return {}
            
        except Exception as e:
            logger.error(f"Error getting existing USD/THB data: {e}")
            return {}

    def update_csv_with_multiple_dates(self, exchange_data_list: List[Dict], csv_path: str = None) -> bool:
        """อัปเดตไฟล์ CSV ด้วยข้อมูลหลายวัน และตรวจสอบการเปลี่ยนแปลง"""
        try:
            if not csv_path:
                csv_path = "e:\\year4_1\\T.Boat\\programs\\perfect\\data\\only_2_stations.csv"
            
            # Read existing CSV
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date']).dt.date
            else:
                logger.error("CSV file not found")
                return False
            
            # Get existing USD_BATH data for comparison
            existing_data = self.get_existing_usd_thb_data(csv_path)
            
            changes_made = False
            today = datetime.now().date()
            
            # Process each exchange rate record
            for exchange_data in exchange_data_list:
                target_date = exchange_data['date']
                new_rate = exchange_data['usd_thb_rate']
                
                # Check if this date exists in CSV
                date_mask = df['Date'] == target_date
                date_exists = date_mask.any()
                
                if date_exists:
                    # Check if we need to update existing data
                    existing_rate = existing_data.get(target_date)
                    
                    if existing_rate is None:
                        # No existing rate, add new one
                        df.loc[date_mask, 'USD_BATH'] = new_rate
                        logger.info(f"Added USD_BATH for {target_date}: {new_rate}")
                        changes_made = True
                        
                    elif abs(existing_rate - new_rate) > 0.0001:  # Check for significant change
                        # Rate has changed, update it
                        df.loc[date_mask, 'USD_BATH'] = new_rate
                        logger.info(f"Updated USD_BATH for {target_date}: {existing_rate} -> {new_rate}")
                        changes_made = True
                        
                    else:
                        logger.info(f"USD_BATH for {target_date} unchanged: {new_rate}")
                
                else:
                    logger.warning(f"Date {target_date} not found in CSV - cannot add exchange rate")
            
            # Handle today's date specifically - use latest available rate
            if exchange_data_list:
                latest_data = exchange_data_list[0]  # Assuming sorted by date desc
                latest_date = latest_data['date']
                latest_rate = latest_data['usd_thb_rate']
                
                # If today's data doesn't exist on the website, use latest available
                today_mask = df['Date'] == today
                today_exists = today_mask.any()
                
                if today_exists:
                    existing_today_rate = existing_data.get(today)
                    
                    if existing_today_rate is None:
                        # Use latest available rate for today
                        df.loc[today_mask, 'USD_BATH'] = latest_rate
                        logger.info(f"Filled today's USD_BATH ({today}) with latest rate from {latest_date}: {latest_rate}")
                        changes_made = True
                        
                    elif latest_date == today and abs(existing_today_rate - latest_rate) > 0.0001:
                        # Today's data is available and different
                        df.loc[today_mask, 'USD_BATH'] = latest_rate
                        logger.info(f"Updated today's USD_BATH ({today}): {existing_today_rate} -> {latest_rate}")
                        changes_made = True
            
            # Save CSV only if changes were made
            if changes_made:
                df.to_csv(csv_path, index=False)
                logger.info(f"CSV file updated successfully: {csv_path}")
            else:
                logger.info("No changes needed in CSV file")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating CSV file: {e}")
            return False

    def run(self) -> bool:
        """รันกระบวนการ scraping (สำหรับ Smart Scraper)"""
        return self.run_scraping()
        
    def run_scraping(self) -> bool:
        """รันกระบวนการ scraping และอัปเดตข้อมูลหลายวัน"""
        try:
            logger.info("=== Starting BOT USD/THB Scraping ===")
            
            # Scrape new data
            scraped_result = self.scrape_usd_thb_rate()
            
            if not scraped_result or 'exchange_data' not in scraped_result:
                logger.warning("Failed to scrape new data, using fallback...")
                
                # Fallback: use latest rate from CSV
                existing_data = self.get_existing_usd_thb_data()
                if existing_data:
                    # Get latest rate
                    latest_date = max(existing_data.keys())
                    latest_rate = existing_data[latest_date]
                    
                    scraped_result = {
                        'exchange_data': [{
                            'date': datetime.now().date(),
                            'usd_thb_rate': latest_rate,
                            'source': 'CSV_fallback'
                        }]
                    }
                    logger.info(f"Using fallback rate from {latest_date}: {latest_rate}")
                else:
                    logger.error("No fallback data available")
                    return False
            
            exchange_data_list = scraped_result['exchange_data']
            logger.info(f"Processing {len(exchange_data_list)} exchange rate records")
            
            # Update CSV file with all available data
            if not self.update_csv_with_multiple_dates(exchange_data_list):
                logger.error("Failed to update CSV file")
                return False
            
            logger.info("=== USD/THB scraping completed successfully ===")
            return True
            
        except Exception as e:
            logger.error(f"Error in run_scraping: {e}")
            return False

def main():
    """Main function for testing"""
    scraper = BOTUSDTHBScraper()
    success = scraper.run_scraping()
    
    if success:
        print("✅ BOT USD/THB scraping completed successfully!")
    else:
        print("❌ BOT USD/THB scraping failed!")
        exit(1)

if __name__ == "__main__":
    main()