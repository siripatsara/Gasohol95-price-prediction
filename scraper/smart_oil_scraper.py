#!/usr/bin/env python3
"""
Smart Oil Pric        # Initialize scrapers
        self.scrapers = {
            'eppo': DirectIframeScraper(),
            'brent': BrentOilScraper(),
            'usd_thb': BOTUSDTHBScraper(),  # ใช้ key เดิม
            'levy': EppoLevyScraper()
        }er with Change Detection
ตรวจสอบการเปลี่ยนแปลงและอัพเดตเฉพาะข้อมูลที่เปล                # บันทึกข้อมูลลง CSV
                self.update_csv_smart(scraped_data, list(scraped_data.keys()))
                
                # ซิงค์ไป PostgreSQL
                self.sync_to_postgresql()
                
                # บันทึก cache สำหรับเปรียบเทียบตอนบ่าย
                self.save_comparison_cache(scraped_data)
                
                logger.info("✅ Morning scraping completed - data cached for afternoon comparison")
                return Trueจริง
"""

import os
import sys
import pandas as pd
import logging
from datetime import datetime, date
from pathlib import Path
import json

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from scraper.direct_iframe_scraper import DirectIframeScraper
from scraper.brent_oil_scraper import BrentOilScraper
from scraper.bot_usd_thb_scraper import BOTUSDTHBScraper
from scraper.eppo_levy_scraper import EPPOLevyScraper
from scraper.realtime_data_manager import RealtimeDataManager

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/smart_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import PostgreSQL sync capability
POSTGRES_AVAILABLE = False
try:
    import sys
    import os
    # Add scripts directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    scripts_dir = os.path.join(parent_dir, "scripts")
    
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    
    # Try importing the sync module (dynamic import)
    from csv_to_postgres_sync import CSVToPostgreSync  # type: ignore
    POSTGRES_AVAILABLE = True
    logger.info("✅ PostgreSQL sync capability loaded")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"⚠️ PostgreSQL sync not available: {e}")

class SmartOilPriceScraper:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"
        self.csv_file = self.data_dir / "only_2_stations.csv"
        self.realtime_file = self.data_dir / "realtime_scraped_data.csv"
        self.comparison_cache = self.data_dir / "comparison_cache.json"
        
        # Initialize scrapers
        self.scrapers = {
            'eppo': DirectIframeScraper(),
            'brent': BrentOilScraper(),
            'usd_thb': BOTUSDTHBScraper(),
            'levy': EPPOLevyScraper()
        }
        
        self.realtime_manager = RealtimeDataManager()
        
        # Initialize PostgreSQL syncer if available
        self.postgres_syncer = None
        if POSTGRES_AVAILABLE:
            try:
                self.postgres_syncer = CSVToPostgreSync()
                logger.info("✅ PostgreSQL syncer initialized")
            except Exception as e:
                logger.warning(f"⚠️ PostgreSQL syncer initialization failed: {e}")
    
    def sync_to_postgresql(self):
        """ซิงค์ข้อมูลไป PostgreSQL หลังจากอัพเดต CSV"""
        if not POSTGRES_AVAILABLE or not self.postgres_syncer:
            logger.info("PostgreSQL sync skipped - not available")
            return False
        
        try:
            logger.info("🔄 Starting PostgreSQL sync...")
            success = self.postgres_syncer.sync_data()
            
            if success:
                logger.info("✅ PostgreSQL sync completed successfully")
                return True
            else:
                logger.error("❌ PostgreSQL sync failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ PostgreSQL sync error: {e}")
            return False
    
    def get_current_time_context(self):
        """ตรวจสอบว่าตอนนี้เป็นเวลา 01:00 หรือ 13:00"""
        current_hour = datetime.now().hour
        
        if current_hour == 1:
            return 'morning', '01:00 AM - Full scraping'
        elif current_hour == 13:
            return 'afternoon', '13:00 PM - Smart update'
        else:
            return 'other', f'{current_hour}:00 - Manual execution'
    
    def load_previous_data(self):
        """โหลดข้อมูลล่าสุดจาก CSV"""
        try:
            if self.csv_file.exists():
                df = pd.read_csv(self.csv_file)
                df['Date'] = pd.to_datetime(df['Date']).dt.date
                
                # ดึงข้อมูลวันนี้หากมี
                today = date.today()
                today_data = df[df['Date'] == today]
                
                if not today_data.empty:
                    latest_record = today_data.iloc[-1].to_dict()
                    logger.info(f"Found existing data for today: {latest_record}")
                    return latest_record
                else:
                    logger.info("No existing data for today")
                    return None
            else:
                logger.info("No CSV file found")
                return None
                
        except Exception as e:
            logger.error(f"Error loading previous data: {e}")
            return None
    
    def save_comparison_cache(self, data):
        """บันทึกข้อมูลสำหรับเปรียบเทียบครั้งถัดไป"""
        try:
            # แปลง date objects เป็น string สำหรับ JSON
            cache_data = {}
            for key, value in data.items():
                if isinstance(value, date):
                    cache_data[key] = value.isoformat()
                else:
                    cache_data[key] = value
            
            with open(self.comparison_cache, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'data': cache_data
                }, f, indent=2)
                
            logger.info(f"Comparison cache saved: {self.comparison_cache}")
            
        except Exception as e:
            logger.error(f"Error saving comparison cache: {e}")
    
    def load_comparison_cache(self):
        """โหลดข้อมูลสำหรับเปรียบเทียบ"""
        try:
            if self.comparison_cache.exists():
                with open(self.comparison_cache, 'r') as f:
                    cache = json.load(f)
                
                # ตรวจสอบว่าข้อมูลใน cache เป็นวันนี้หรือไม่
                cache_date = datetime.fromisoformat(cache['timestamp']).date()
                today = date.today()
                
                if cache_date == today:
                    logger.info("Found comparison cache for today")
                    return cache['data']
                else:
                    logger.info(f"Cache is from {cache_date}, not today ({today})")
                    return None
            else:
                logger.info("No comparison cache found")
                return None
                
        except Exception as e:
            logger.error(f"Error loading comparison cache: {e}")
            return None
    
    def scrape_all_sources(self):
        """Scrape ข้อมูลจากทุกแหล่ง"""
        scraped_data = {}
        success_count = 0
        
        logger.info("=== Starting comprehensive scraping ===")
        
        # 1. EPPO Oil Prices (PTT/Shell)
        try:
            logger.info("Scraping EPPO oil prices...")
            eppo_scraper = self.scrapers['eppo']
            eppo_data = eppo_scraper.scrape_iframe_directly()
            
            if eppo_data:
                scraped_data.update({
                    'price_PTT': eppo_data.get('price_ptt'),
                    'price_Shell': eppo_data.get('price_shell'),
                    'effective_date': eppo_data.get('effective_date')
                })
                success_count += 1
                logger.info(f"EPPO: PTT={eppo_data.get('price_ptt')}, Shell={eppo_data.get('price_shell')}")
            else:
                logger.warning("EPPO scraping failed")
                
        except Exception as e:
            logger.error(f"❌ EPPO scraping error: {e}")
        
        # 2. Brent Oil Price
        try:
            logger.info("Scraping Brent oil price...")
            brent_scraper = self.scrapers['brent']
            brent_data = brent_scraper.run()  # ใช้ run() method
            
            if brent_data:
                # อ่านข้อมูลล่าสุดจาก CSV
                df = pd.read_csv(self.csv_file)
                latest_brent = df['Price_Brent'].iloc[-1] if 'Price_Brent' in df.columns else None
                scraped_data['Price_Brent'] = latest_brent
                success_count += 1
                logger.info(f"EPPO: Brent={latest_brent}")
            else:
                logger.warning("Brent scraping failed")
                
        except Exception as e:
            logger.error(f"Brent scraping error: {e}")
        
        # 3. USD/THB Exchange Rate
        try:
            logger.info("Scraping USD/THB exchange rate...")
            bot_scraper = self.scrapers['usd_thb']  # แก้ไขให้ตรงกับ key ใน scrapers dict
            bot_data = bot_scraper.run()  # ใช้ run() method
            
            if bot_data:
                # อ่านข้อมูลล่าสุดจาก CSV
                df = pd.read_csv(self.csv_file)
                latest_usd_bath = df['USD_BATH'].iloc[-1] if 'USD_BATH' in df.columns else None
                scraped_data['USD_BATH'] = latest_usd_bath
                success_count += 1
                logger.info(f"BOT: USD_BATH={latest_usd_bath}")
            else:
                logger.warning("BOT USD/THB scraping failed")
                
        except Exception as e:
            logger.error(f"BOT USD/THB scraping error: {e}")
        
        # 4. Oil Fund Levy
        try:
            logger.info("Scraping Oil Fund Levy...")
            levy_scraper = self.scrapers['levy']
            
            # Levy scraper มีการจัดการข้อมูลเองแล้ว เราจึงเรียกใช้และดูผลลัพธ์
            levy_success = levy_scraper.run()
            
            if levy_success:
                # อ่านข้อมูลล่าสุดจาก CSV
                df = pd.read_csv(self.csv_file)
                latest_levy = df['Price_Levy'].iloc[-1] if 'Price_Levy' in df.columns else None
                scraped_data['Price_Levy'] = latest_levy
                success_count += 1
                logger.info(f"Levy: {latest_levy}")
            else:
                logger.warning("Levy scraping failed")
                
        except Exception as e:
            logger.error(f"Levy scraping error: {e}")
        
        logger.info(f"=== Scraping completed: {success_count}/4 sources successful ===")
        return scraped_data
    
    def compare_and_detect_changes(self, new_data, previous_data):
        """เปรียบเทียบข้อมูลใหม่กับข้อมูลเก่า"""
        if not previous_data:
            logger.info("No previous data to compare - treating all as new")
            return new_data, list(new_data.keys())
        
        changes = []
        updated_data = previous_data.copy()
        
        # Fields to compare
        compare_fields = ['price_PTT', 'price_Shell', 'Price_Brent', 'USD_BATH', 'Price_Levy', 'effective_date']
        
        for field in compare_fields:
            if field in new_data and new_data[field] is not None:
                old_value = previous_data.get(field)
                new_value = new_data[field]
                
                # เปรียบเทียบค่า
                if old_value != new_value:
                    changes.append({
                        'field': field,
                        'old_value': old_value,
                        'new_value': new_value
                    })
                    updated_data[field] = new_value
                    logger.info(f"🔄 Change detected in {field}: {old_value} → {new_value}")
                else:
                    logger.info(f"✅ No change in {field}: {old_value}")
        
        return updated_data, [change['field'] for change in changes]
    
    def update_csv_smart(self, final_data, changed_fields):
        """อัพเดต CSV อย่างชาญฉลาด"""
        try:
            today = date.today()
            
            # อ่าน CSV ปัจจุบัน
            if self.csv_file.exists():
                df = pd.read_csv(self.csv_file)
                df['Date'] = pd.to_datetime(df['Date']).dt.date
            else:
                # สร้าง DataFrame ใหม่หากไม่มีไฟล์
                columns = ['Date', 'price_PTT', 'price_Shell', 'effective_date', 'Price_Brent', 'USD_BATH', 'Price_Levy']
                df = pd.DataFrame(columns=columns)
            
            # ตรวจสอบว่ามีข้อมูลวันนี้หรือไม่
            today_mask = df['Date'] == today
            
            if today_mask.any():
                # อัพเดตข้อมูลวันนี้เฉพาะ fields ที่เปลี่ยน
                if changed_fields:
                    for field in changed_fields:
                        if field in final_data:
                            df.loc[today_mask, field] = final_data[field]
                    logger.info(f"Updated existing record for {today} - changed fields: {changed_fields}")
                else:
                    logger.info(f"No changes needed for {today}")
            else:
                # เพิ่มข้อมูลใหม่
                new_row = {'Date': today}
                new_row.update(final_data)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                logger.info(f"Added new record for {today}")
            
            # เรียงลำดับและบันทึก
            df = df.sort_values('Date')
            df.to_csv(self.csv_file, index=False)
            logger.info(f"CSV updated successfully: {self.csv_file}")
            
            # อัพเดต realtime file ด้วย
            self.realtime_manager.add_realtime_data(today, **final_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating CSV: {e}")
            return False
    
    def run_smart_scraping(self):
        """รัน smart scraping ตามเวลา"""
        time_context, description = self.get_current_time_context()
        
        logger.info(f"=== Smart Oil Price Scraping ===")
        logger.info(f"Execution time: {description}")
        logger.info(f"Context: {time_context}")
        
        if time_context == 'morning':
            # 1 AM - Full scraping
            logger.info("🌅 Morning execution (1 AM) - Full data collection")
            
            scraped_data = self.scrape_all_sources()
            
            if scraped_data:
                # บันทึกข้อมูลทั้งหมด
                self.update_csv_smart(scraped_data, list(scraped_data.keys()))
                
                # บันทึก cache สำหรับเปรียบเทียบตอนบ่าย
                self.save_comparison_cache(scraped_data)
                
                logger.info("✅ Morning scraping completed - data cached for afternoon comparison")
                return True
            else:
                logger.error("❌ Morning scraping failed - no data collected")
                return False
                
        elif time_context == 'afternoon':
            # 1 PM - Smart update
            logger.info("🌆 Afternoon execution (1 PM) - Smart change detection")
            
            # โหลดข้อมูลตอนเช้า
            morning_data = self.load_comparison_cache()
            if not morning_data:
                logger.warning("No morning data found - falling back to full scraping")
                scraped_data = self.scrape_all_sources()
                self.update_csv_smart(scraped_data, list(scraped_data.keys()))
                return True
            
            # Scrape ข้อมูลใหม่
            new_scraped_data = self.scrape_all_sources()
            
            if new_scraped_data:
                # เปรียบเทียบและตรวจหาการเปลี่ยนแปลง
                final_data, changed_fields = self.compare_and_detect_changes(new_scraped_data, morning_data)
                
                if changed_fields:
                    logger.info(f"📈 Changes detected in: {', '.join(changed_fields)}")
                    self.update_csv_smart(final_data, changed_fields)
                    
                    # ซิงค์ไป PostgreSQL
                    self.sync_to_postgresql()
                    
                    logger.info("✅ Afternoon scraping completed - data updated with changes")
                else:
                    logger.info("✅ Afternoon scraping completed - no changes detected")
                
                return True
            else:
                logger.error("❌ Afternoon scraping failed - no data collected")
                return False
        
        else:
            # Manual execution - Full scraping
            logger.info("Manual execution - Full data collection")
            scraped_data = self.scrape_all_sources()
            
            if scraped_data:
                self.update_csv_smart(scraped_data, list(scraped_data.keys()))
                
                # ซิงค์ไป PostgreSQL
                self.sync_to_postgresql()
                
                logger.info("Manual scraping completed")
                return True
            else:
                logger.error("Manual scraping failed")
                return False

def main():
    """Main function for testing"""
    scraper = SmartOilPriceScraper()
    success = scraper.run_smart_scraping()
    
    if success:
        print("✅ Smart oil price scraping completed successfully!")
    else:
        print("❌ Smart oil price scraping failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()