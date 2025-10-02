#!/usr/bin/env python3
"""
Enhanced EPPO Oil Price Scraper with Selenium
ดึงข้อมูลราคาน้ำมันจากเว็บไซต์ EPPO ด้วย Selenium
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
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EPPOOilScraperSelenium:
    def __init__(self):
        self.base_url = "https://www.eppo.go.th/epposite/index.php/th/petroleum/price/oil-price"
        
        # Database connection parameters
        self.db_config = {
            'host': 'localhost',
            'port': 5435,
            'database': 'gasohol_prediction', 
            'user': 'postgres',
            'password': 'postgres123'
        }
        
        self.driver = None

    def setup_driver(self):
        """ตั้งค่า Chrome WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in background
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # Use WebDriverManager to automatically download ChromeDriver
            service = Service(ChromeDriverManager().install())
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome WebDriver initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            return False

    def get_db_connection(self):
        """สร้างการเชื่อมต่อฐานข้อมูล"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None

    def scrape_oil_prices(self) -> Optional[Dict]:
        """ดึงข้อมูลราคาน้ำมันจากเว็บ EPPO ด้วย Selenium"""
        try:
            if not self.setup_driver():
                return None
                
            logger.info("Starting oil price scraping with Selenium...")
            
            # Navigate to the page
            self.driver.get(self.base_url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Try to find the oil price table/content
            # Look for various possible selectors
            selectors_to_try = [
                '.div_oil_price',
                '[class*="oil_price"]',
                '[class*="oil"]',
                'iframe',  # Check if content is in iframe
            ]
            
            oil_content = None
            for selector in selectors_to_try:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.info(f"Found elements with selector: {selector}")
                        oil_content = elements[0]
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # If no direct oil content found, check for iframe
            if not oil_content:
                try:
                    iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
                    for iframe in iframes:
                        iframe_src = iframe.get_attribute('src')
                        logger.info(f"Found iframe: {iframe_src}")
                        
                        # Look for specific iframe with oil data
                        if iframe_src and ('eppo_oil_gen_new.php' in iframe_src or 'oil' in iframe_src.lower()):
                            logger.info("Switching to oil price iframe")
                            self.driver.switch_to.frame(iframe)
                            
                            # Wait for iframe content to load
                            time.sleep(3)
                            
                            # Now get the iframe content
                            iframe_source = self.driver.page_source
                            iframe_soup = BeautifulSoup(iframe_source, 'html.parser')
                            
                            # Save iframe content for debugging
                            with open('iframe_content.html', 'w', encoding='utf-8') as f:
                                f.write(iframe_source)
                            logger.info("Iframe content saved to iframe_content.html")
                            
                            # Extract data from iframe
                            iframe_data = self.extract_price_data(iframe_soup)
                            if iframe_data:
                                return iframe_data
                            
                            # Switch back to main frame
                            self.driver.switch_to.default_content()
                            break
                except Exception as e:
                    logger.error(f"Iframe handling failed: {e}")
                    self.driver.switch_to.default_content()
            
            # Get page source and parse with BeautifulSoup
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Save current page for debugging
            with open('current_page_selenium.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            logger.info("Current page saved to current_page_selenium.html")
            
            # Look for price data in the parsed HTML
            gasohol_data = self.extract_price_data(soup)
            
            return gasohol_data
            
        except Exception as e:
            logger.error(f"Error scraping oil prices with Selenium: {e}")
            return None
            
        finally:
            if self.driver:
                self.driver.quit()

    def extract_price_data(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract price data from BeautifulSoup object"""
        try:
            # Method 1: Look for div_oil_price class
            oil_price_div = soup.find('div', class_='div_oil_price')
            if oil_price_div:
                logger.info("Found div_oil_price container")
                return self.parse_oil_price_div(oil_price_div)
            
            # Method 2: Look for any div with price-like content
            price_pattern = re.compile(r'\b\d{2}\.\d{2}\b')  # Pattern like 32.65
            
            # Search for text that looks like prices
            page_text = soup.get_text()
            price_matches = price_pattern.findall(page_text)
            
            if price_matches:
                logger.info(f"Found potential prices: {price_matches[:10]}")
                
                # Try to find price data in table-like structures
                tables = soup.find_all('table')
                for table in tables:
                    table_text = table.get_text()
                    if any(price in table_text for price in price_matches[:5]):
                        logger.info("Found prices in table structure")
                        return self.parse_table_prices(table, price_matches)
                
                # Try to find price data in div structures
                divs = soup.find_all('div')
                for div in divs:
                    div_text = div.get_text()
                    if len(price_pattern.findall(div_text)) >= 2:  # At least 2 prices
                        logger.info("Found prices in div structure")
                        return self.parse_div_prices(div, price_matches)
            
            # Method 3: Look for specific Thai text patterns
            thai_patterns = [
                r'แก๊สโซฮอล.*?(\d{2}\.\d{2})',
                r'Gasohol.*?(\d{2}\.\d{2})',
                r'PTT.*?(\d{2}\.\d{2})',
                r'Shell.*?(\d{2}\.\d{2})'
            ]
            
            for pattern in thai_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    logger.info(f"Found price with pattern {pattern}: {matches}")
            
            logger.error("Could not extract price data from any method")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting price data: {e}")
            return None

    def parse_oil_price_div(self, oil_price_div) -> Optional[Dict]:
        """Parse the official oil price div structure"""
        try:
            # Extract date from header
            date_header = oil_price_div.find('div', string=re.compile(r'Oil price.*\d+.*\w+.*\d+'))
            scraped_date = datetime.now().date()
            
            if date_header:
                date_text = date_header.get_text()
                date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', date_text)
                if date_match:
                    try:
                        scraped_date = datetime.strptime(date_match.group(1), "%d %b %Y").date()
                    except:
                        pass
            
            # Find gasohol 95 prices
            gasohol_data = {'date': scraped_date}
            
            # Look for price rows
            price_rows = oil_price_div.find_all('div', class_=['oil_price_colum_name_odd', 'oil_price_colum_name_even'])
            
            for row in price_rows:
                # Check if this is gasohol 95 row
                img_tag = row.find('img')
                if img_tag and 'oil_name2.png' in img_tag.get('src', ''):
                    price_columns = row.find_all('div', class_='oil_price_colum')
                    
                    if len(price_columns) >= 2:
                        ptt_text = price_columns[0].get_text().strip()
                        shell_text = price_columns[1].get_text().strip()
                        
                        gasohol_data['price_ptt'] = float(ptt_text) if ptt_text != '-' else None
                        gasohol_data['price_shell'] = float(shell_text) if shell_text != '-' else None
                        
                        logger.info(f"Extracted PTT: {gasohol_data['price_ptt']}, Shell: {gasohol_data['price_shell']}")
                        return gasohol_data
            
            return gasohol_data if 'price_ptt' in gasohol_data or 'price_shell' in gasohol_data else None
            
        except Exception as e:
            logger.error(f"Error parsing oil price div: {e}")
            return None

    def parse_table_prices(self, table, price_matches) -> Optional[Dict]:
        """Parse prices from table structure"""
        try:
            # Simple extraction for now - return first two prices found
            if len(price_matches) >= 2:
                return {
                    'date': datetime.now().date(),
                    'price_ptt': float(price_matches[0]),
                    'price_shell': float(price_matches[1]),
                    'effective_date': None
                }
            return None
        except Exception as e:
            logger.error(f"Error parsing table prices: {e}")
            return None

    def parse_div_prices(self, div, price_matches) -> Optional[Dict]:
        """Parse prices from div structure"""
        try:
            # Simple extraction for now - return first two prices found
            if len(price_matches) >= 2:
                return {
                    'date': datetime.now().date(),
                    'price_ptt': float(price_matches[0]),
                    'price_shell': float(price_matches[1]),
                    'effective_date': None
                }
            return None
        except Exception as e:
            logger.error(f"Error parsing div prices: {e}")
            return None

    def get_latest_data_from_db(self) -> Optional[Dict]:
        """ดึงข้อมูลล่าสุดจากฐานข้อมูล"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return None
                
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT date, price_ptt, price_shell, effective_date
                    FROM daily_gasohol_prices 
                    ORDER BY date DESC 
                    LIMIT 1
                """)
                result = cursor.fetchone()
                
            conn.close()
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest data from DB: {e}")
            return None

    def forward_fill_missing_data(self, new_data: Dict, latest_db_data: Optional[Dict]) -> Dict:
        """Forward fill ข้อมูลที่ขาดหายด้วยข้อมูลล่าสุด"""
        if not latest_db_data:
            return new_data
            
        filled_data = new_data.copy()
        
        # Forward fill PTT price
        if filled_data.get('price_ptt') is None and latest_db_data.get('price_ptt'):
            filled_data['price_ptt'] = latest_db_data['price_ptt']
            logger.info(f"Forward filled PTT price: {filled_data['price_ptt']}")
            
        # Forward fill Shell price  
        if filled_data.get('price_shell') is None and latest_db_data.get('price_shell'):
            filled_data['price_shell'] = latest_db_data['price_shell']
            logger.info(f"Forward filled Shell price: {filled_data['price_shell']}")
            
        return filled_data

    def save_to_database(self, data: Dict) -> bool:
        """บันทึกข้อมูลลงฐานข้อมูล"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
                
            with conn.cursor() as cursor:
                # Check if data for this date already exists
                cursor.execute("""
                    SELECT id FROM daily_gasohol_prices WHERE date = %s
                """, (data['date'],))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    cursor.execute("""
                        UPDATE daily_gasohol_prices 
                        SET price_ptt = %s, price_shell = %s, effective_date = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE date = %s
                    """, (data['price_ptt'], data['price_shell'], data.get('effective_date'), data['date']))
                    logger.info(f"Updated existing record for {data['date']}")
                else:
                    # Insert new record
                    cursor.execute("""
                        INSERT INTO daily_gasohol_prices (date, price_ptt, price_shell, effective_date)
                        VALUES (%s, %s, %s, %s)
                    """, (data['date'], data['price_ptt'], data['price_shell'], data.get('effective_date')))
                    logger.info(f"Inserted new record for {data['date']}")
                
                conn.commit()
                
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            return False

    def update_csv_file(self, new_data: Dict, csv_path: str = None) -> bool:
        """อัปเดตไฟล์ CSV ด้วยข้อมูลใหม่"""
        try:
            if not csv_path:
                csv_path = "e:\\year4_1\\T.Boat\\programs\\perfect\\data\\only_2_stations.csv"
            
            # Read existing CSV
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                df['Date'] = pd.to_datetime(df['Date']).dt.date
            else:
                # Create new DataFrame if file doesn't exist
                df = pd.DataFrame(columns=['Date', 'price_PTT', 'price_Shell', 'effective_date'])
            
            # Check if date already exists
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
            df = df.sort_values('Date')
            df.to_csv(csv_path, index=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating CSV file: {e}")
            return False

    def run_scraping(self) -> bool:
        """รันกระบวนการ scraping ทั้งหมด"""
        try:
            logger.info("=== Starting EPPO Oil Price Scraping with Selenium ===")
            
            # Scrape new data
            new_data = self.scrape_oil_prices()
            if not new_data:
                logger.error("Failed to scrape new data")
                return False
            
            # Get latest data from database for forward filling
            latest_db_data = self.get_latest_data_from_db()
            
            # Forward fill missing data
            filled_data = self.forward_fill_missing_data(new_data, latest_db_data)
            
            # Validate that we have at least some price data
            if filled_data.get('price_ptt') is None and filled_data.get('price_shell') is None:
                logger.error("No valid price data after forward filling")
                return False
            
            # Save to database (skip for now to test scraping first)
            # if not self.save_to_database(filled_data):
            #     logger.error("Failed to save to database")
            #     return False
            
            # Update CSV file
            if not self.update_csv_file(filled_data):
                logger.error("Failed to update CSV file")
                return False
            
            logger.info(f"Successfully scraped and saved data for {filled_data['date']}")
            logger.info(f"PTT: {filled_data['price_ptt']}, Shell: {filled_data['price_shell']}")
            logger.info("=== Scraping completed successfully ===")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in run_scraping: {e}")
            return False

def main():
    """Main function for testing"""
    scraper = EPPOOilScraperSelenium()
    success = scraper.run_scraping()
    
    if success:
        print("Scraping completed successfully!")
    else:
        print("Scraping failed!")
        exit(1)

if __name__ == "__main__":
    main()