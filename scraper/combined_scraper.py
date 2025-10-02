#!/usr/bin/env python3
"""
Combined Oil Price Scraper
รวม scraper ทั้งหมด: EPPO Oil Prices, Brent Oil, และ USD/THB
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from direct_iframe_scraper import DirectIframeScraper
from brent_oil_scraper import BrentOilScraper
from usd_thb_scraper import USDTHBScraper
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CombinedOilScraper:
    def __init__(self, csv_path: str = None):
        self.csv_path = csv_path or "e:\\year4_1\\T.Boat\\programs\\perfect\\data\\only_2_stations.csv"
        
        # Initialize individual scrapers
        self.eppo_scraper = DirectIframeScraper()
        self.brent_scraper = BrentOilScraper()
        self.usd_thb_scraper = USDTHBScraper()

    def run_complete_scraping(self) -> bool:
        """รัน scraping ทั้งหมดตามลำดับ"""
        try:
            logger.info("🛢️ === Starting Complete Oil Price Scraping ===")
            
            results = {
                'eppo': False,
                'brent': False,
                'usd_thb': False
            }
            
            # 1. Scrape EPPO Oil Prices (PTT, Shell)
            logger.info("📊 Step 1: Scraping EPPO oil prices...")
            try:
                results['eppo'] = self.eppo_scraper.run_scraping()
                if results['eppo']:
                    logger.info("✅ EPPO scraping completed successfully")
                else:
                    logger.error("❌ EPPO scraping failed")
            except Exception as e:
                logger.error(f"❌ EPPO scraping error: {e}")
            
            # 2. Scrape Brent Oil Prices
            logger.info("🛢️ Step 2: Scraping Brent oil prices...")
            try:
                results['brent'] = self.brent_scraper.run_brent_scraping()
                if results['brent']:
                    logger.info("✅ Brent oil scraping completed successfully")
                else:
                    logger.error("❌ Brent oil scraping failed")
            except Exception as e:
                logger.error(f"❌ Brent oil scraping error: {e}")
            
            # 3. Scrape USD/THB Exchange Rate
            logger.info("💱 Step 3: Scraping USD/THB exchange rate...")
            try:
                results['usd_thb'] = self.usd_thb_scraper.run_usd_thb_scraping()
                if results['usd_thb']:
                    logger.info("✅ USD/THB scraping completed successfully")
                else:
                    logger.error("❌ USD/THB scraping failed")
            except Exception as e:
                logger.error(f"❌ USD/THB scraping error: {e}")
            
            # 4. Summary and validation
            success_count = sum(results.values())
            total_count = len(results)
            
            logger.info(f"📋 Scraping Summary: {success_count}/{total_count} successful")
            logger.info(f"   - EPPO Oil Prices: {'✅' if results['eppo'] else '❌'}")
            logger.info(f"   - Brent Oil Price: {'✅' if results['brent'] else '❌'}")
            logger.info(f"   - USD/THB Rate: {'✅' if results['usd_thb'] else '❌'}")
            
            # 5. Final data validation
            if success_count > 0:
                self.validate_final_data()
            
            overall_success = success_count == total_count
            
            if overall_success:
                logger.info("🎉 === Complete Oil Price Scraping SUCCESSFUL ===")
            else:
                logger.warning(f"⚠️ === Partial Success: {success_count}/{total_count} scrapers completed ===")
            
            return overall_success
            
        except Exception as e:
            logger.error(f"💥 Critical error in combined scraping: {e}")
            return False

    def validate_final_data(self) -> Dict:
        """ตรวจสอบและแสดงข้อมูลสุดท้าย"""
        try:
            logger.info("🔍 Validating final data...")
            
            if not os.path.exists(self.csv_path):
                logger.error(f"CSV file not found: {self.csv_path}")
                return {}
            
            df = pd.read_csv(self.csv_path)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            
            # Get today's data
            today = datetime.now().date()
            today_data = df[df['Date'] == today]
            
            if today_data.empty:
                logger.warning(f"No data found for today ({today})")
                latest_data = df.tail(1)
            else:
                latest_data = today_data.tail(1)
            
            if not latest_data.empty:
                row = latest_data.iloc[0]
                
                validation_result = {
                    'date': row['Date'],
                    'price_ptt': row.get('price_PTT'),
                    'price_shell': row.get('price_Shell'),
                    'effective_date': row.get('effective_date'),
                    'price_brent': row.get('Price_Brent'),
                    'usd_thb': row.get('USD_BATH'),
                    'price_levy': row.get('Price_Levy')
                }
                
                logger.info("📊 Latest Data Summary:")
                logger.info(f"   📅 Date: {validation_result['date']}")
                logger.info(f"   ⛽ PTT Price: {validation_result['price_ptt']} THB/L")
                logger.info(f"   ⛽ Shell Price: {validation_result['price_shell']} THB/L") 
                logger.info(f"   📅 Effective: {validation_result['effective_date']}")
                logger.info(f"   🛢️ Brent Oil: ${validation_result['price_brent']}/barrel")
                logger.info(f"   💱 USD/THB: {validation_result['usd_thb']}")
                
                # Check for missing data
                missing_fields = []
                if pd.isna(validation_result['price_ptt']) and pd.isna(validation_result['price_shell']):
                    missing_fields.append("Oil Prices")
                if pd.isna(validation_result['price_brent']):
                    missing_fields.append("Brent Oil")
                if pd.isna(validation_result['usd_thb']):
                    missing_fields.append("USD/THB")
                
                if missing_fields:
                    logger.warning(f"⚠️ Missing data: {', '.join(missing_fields)}")
                else:
                    logger.info("✅ All data fields are complete")
                
                return validation_result
            
            return {}
            
        except Exception as e:
            logger.error(f"Error validating final data: {e}")
            return {}

    def run_with_retry(self, max_retries: int = 2) -> bool:
        """รัน scraping พร้อม retry mechanism"""
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"🔄 Attempt {attempt + 1}/{max_retries + 1}")
                
                success = self.run_complete_scraping()
                
                if success:
                    return True
                
                if attempt < max_retries:
                    logger.info(f"⏳ Retrying in 30 seconds...")
                    import time
                    time.sleep(30)
                
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries:
                    import time
                    time.sleep(30)
        
        logger.error("❌ All retry attempts failed")
        return False

def main():
    """Main function for testing"""
    scraper = CombinedOilScraper()
    
    # Run with retry
    success = scraper.run_with_retry(max_retries=1)
    
    if success:
        print("\n🎉 ===== COMPLETE SCRAPING SUCCESSFUL! =====")
        print("✅ All oil price data has been updated successfully!")
    else:
        print("\n❌ ===== SCRAPING FAILED =====")
        print("⚠️ Some or all scraping operations failed. Check logs for details.")
        exit(1)

if __name__ == "__main__":
    main()