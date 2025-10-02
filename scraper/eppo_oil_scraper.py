#!/usr/bin/env python3
"""
EPPO Oil Price Scraper
ดึงข้อมูลราคาน้ำมันจากเว็บไซต์ EPPO
https://www.eppo.go.th/epposite/index.php/th/petroleum/price/oil-price
"""

import requests
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

class EPPOOilScraper:
    def __init__(self):
        self.base_url = "https://www.eppo.go.th/epposite/index.php/th/petroleum/price/oil-price"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Database connection parameters
        self.db_config = {
            'host': 'localhost',
            'port': 5435,
            'database': 'gasohol_prediction', 
            'user': 'postgres',
            'password': 'postgres123'
        }
        
        # Oil station column mapping (0-indexed)
        # Based on the HTML structure provided
        self.station_mapping = {
            0: 'PTT',      # First column
            1: 'Shell',    # Second column  
            2: 'Esso',     # Third column
            3: 'Chevron',  # Fourth column (skipped in HTML)
            4: 'Bangchak', # Fifth column
            5: 'IRPC',     # Sixth column
            6: 'Susco',    # Seventh column
            7: 'Pure',     # Eighth column
            8: 'Kaset',    # Ninth column
            9: 'Pt'        # Tenth column
        }

    def get_db_connection(self):
        """สร้างการเชื่อมต่อฐานข้อมูล"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None

    def scrape_oil_prices(self) -> Optional[Dict]:
        """ดึงข้อมูลราคาน้ำมันจากเว็บ EPPO"""
        try:
            logger.info("Starting oil price scraping...")
            
            # Send request with retry mechanism
            for attempt in range(3):
                try:
                    response = requests.get(self.base_url, headers=self.headers, timeout=30)
                    response.raise_for_status()
                    break
                except requests.RequestException as e:
                    logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                    if attempt == 2:
                        logger.error("All request attempts failed")
                        return None
                    time.sleep(5)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the oil price container
            oil_price_div = soup.find('div', class_='div_oil_price')
            if not oil_price_div:
                logger.error("Could not find oil price container")
                return None
            
            # Extract date from header
            date_header = oil_price_div.find('div', style=lambda x: x and 'Oil price' in str(x))
            if date_header:
                date_text = date_header.get_text()
                date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', date_text)
                if date_match:
                    scraped_date = date_match.group(1)
                    logger.info(f"Found date: {scraped_date}")
                else:
                    scraped_date = datetime.now().strftime("%d %b %Y")
            else:
                scraped_date = datetime.now().strftime("%d %b %Y")
            
            # Parse date to standard format
            try:
                parsed_date = datetime.strptime(scraped_date, "%d %b %Y").date()
            except:
                parsed_date = datetime.now().date()
            
            # Extract gasohol prices (focusing on Gasohol 95)
            gasohol_data = {}
            
            # Find gasohol 95 row (oil_name2.png = Gasohol 95)
            gasohol_rows = oil_price_div.find_all('div', class_=['oil_price_colum_name_odd', 'oil_price_colum_name_even'])
            
            for row in gasohol_rows:
                img_tag = row.find('img')
                if img_tag and 'oil_name2.png' in img_tag.get('src', ''):
                    # This is Gasohol 95 row
                    price_columns = row.find_all('div', class_='oil_price_colum')
                    
                    # Extract PTT and Shell prices (columns 0 and 1)
                    if len(price_columns) >= 2:
                        ptt_price_text = price_columns[0].get_text().strip()
                        shell_price_text = price_columns[1].get_text().strip()
                        
                        # Convert to float, handle '-' values
                        try:
                            ptt_price = float(ptt_price_text) if ptt_price_text != '-' else None
                        except:
                            ptt_price = None
                            
                        try:
                            shell_price = float(shell_price_text) if shell_price_text != '-' else None
                        except:
                            shell_price = None
                        
                        gasohol_data = {
                            'date': parsed_date,
                            'price_ptt': ptt_price,
                            'price_shell': shell_price
                        }
                        
                        logger.info(f"Gasohol 95 prices - PTT: {ptt_price}, Shell: {shell_price}")
                    break
            
            # Extract effective date
            effective_date = None
            effective_rows = oil_price_div.find_all('div', class_=['oil_price_colum_name_odd', 'oil_price_colum_name_even'])
            
            for row in effective_rows:
                if 'Effective date' in row.get_text() or 'มีผลบังคับใช้' in row.get_text():
                    price_columns = row.find_all('div', class_='oil_price_colum')
                    if price_columns:
                        effective_text = price_columns[0].get_text().strip()
                        gasohol_data['effective_date'] = effective_text
                        logger.info(f"Effective date: {effective_text}")
                    break
            
            if not gasohol_data:
                logger.error("Could not extract gasohol price data")
                return None
                
            return gasohol_data
            
        except Exception as e:
            logger.error(f"Error scraping oil prices: {e}")
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
            
        # Forward fill effective date if missing
        if not filled_data.get('effective_date') and latest_db_data.get('effective_date'):
            filled_data['effective_date'] = latest_db_data['effective_date']
            logger.info(f"Forward filled effective date: {filled_data['effective_date']}")
            
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
                    """, (data['price_ptt'], data['price_shell'], data['effective_date'], data['date']))
                    logger.info(f"Updated existing record for {data['date']}")
                else:
                    # Insert new record
                    cursor.execute("""
                        INSERT INTO daily_gasohol_prices (date, price_ptt, price_shell, effective_date)
                        VALUES (%s, %s, %s, %s)
                    """, (data['date'], data['price_ptt'], data['price_shell'], data['effective_date']))
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
                df.loc[mask, 'effective_date'] = new_data['effective_date']
                logger.info(f"Updated CSV row for {new_data['date']}")
            else:
                # Add new row
                new_row = {
                    'Date': new_data['date'],
                    'price_PTT': new_data['price_ptt'],
                    'price_Shell': new_data['price_shell'],
                    'effective_date': new_data['effective_date']
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
            logger.info("=== Starting EPPO Oil Price Scraping ===")
            
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
            
            # Save to database
            if not self.save_to_database(filled_data):
                logger.error("Failed to save to database")
                return False
            
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
    scraper = EPPOOilScraper()
    success = scraper.run_scraping()
    
    if success:
        print("Scraping completed successfully!")
    else:
        print("Scraping failed!")
        exit(1)

if __name__ == "__main__":
    main()