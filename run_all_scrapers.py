#!/usr/bin/env python3
"""
Integrated Oil Price Scraper
รัน scrapers ทั้งหมดและจัดการข้อมูล real-time
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
import subprocess

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from scraper.realtime_data_manager import RealtimeDataManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/integrated_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IntegratedScraper:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.scraper_dir = self.base_dir / "scraper"
        self.realtime_manager = RealtimeDataManager()
        
        # List of scrapers to run
        self.scrapers = [
            {
                'name': 'EPPO Oil Prices',
                'script': 'direct_iframe_scraper.py',
                'description': 'PTT & Shell Gasohol 95 prices'
            },
            {
                'name': 'Brent Oil Prices',
                'script': 'brent_oil_scraper.py', 
                'description': 'FRED Brent crude oil prices'
            },
            {
                'name': 'USD/THB Exchange Rate',
                'script': 'bot_usd_thb_scraper.py',
                'description': 'BOT exchange rates'
            },
            {
                'name': 'EPPO Oil Fund Levy',
                'script': 'eppo_levy_scraper.py',
                'description': 'EPPO Gasohol 95 (E10) levy data'
            }
        ]
    
    def run_scraper(self, scraper_info):
        """รัน scraper ตัวเดียว"""
        try:
            script_path = self.scraper_dir / scraper_info['script']
            if not script_path.exists():
                logger.error(f"Scraper script not found: {script_path}")
                return False
            
            logger.info(f"=== Running {scraper_info['name']} ===")
            logger.info(f"Description: {scraper_info['description']}")
            
            # Run the scraper script
            cmd = [sys.executable, str(script_path)]
            result = subprocess.run(
                cmd,
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info(f"✅ {scraper_info['name']} completed successfully")
                # Log any output from the scraper
                if result.stdout.strip():
                    logger.info(f"Output: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"❌ {scraper_info['name']} failed with return code {result.returncode}")
                if result.stderr.strip():
                    logger.error(f"Error: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ {scraper_info['name']} timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"❌ {scraper_info['name']} failed: {e}")
            return False
    
    def run_all_scrapers(self):
        """รัน scrapers ทั้งหมด"""
        logger.info("=== Starting Integrated Oil Price Scraping ===")
        logger.info(f"Timestamp: {datetime.now()}")
        
        results = {}
        total_scrapers = len(self.scrapers)
        successful_scrapers = 0
        
        for scraper_info in self.scrapers:
            success = self.run_scraper(scraper_info)
            results[scraper_info['name']] = success
            if success:
                successful_scrapers += 1
        
        # Show summary
        logger.info(f"\n=== Scraping Summary ===")
        logger.info(f"Total scrapers: {total_scrapers}")
        logger.info(f"Successful: {successful_scrapers}")
        logger.info(f"Failed: {total_scrapers - successful_scrapers}")
        
        for name, success in results.items():
            status = "✅ Success" if success else "❌ Failed"
            logger.info(f"  {name}: {status}")
        
        # Show realtime data summary
        summary = self.realtime_manager.get_summary()
        logger.info(f"\n=== Realtime Data Summary ===")
        logger.info(f"Total records: {summary.get('total_records', 0)}")
        logger.info(f"Latest date: {summary.get('latest_date', 'N/A')}")
        if 'latest_record' in summary and summary['latest_record']:
            logger.info("Latest record:")
            for key, value in summary['latest_record'].items():
                logger.info(f"  {key}: {value}")
        
        return successful_scrapers == total_scrapers
    
    def get_realtime_summary(self):
        """ดูสรุปข้อมูล real-time"""
        return self.realtime_manager.get_summary()
    
    def view_recent_data(self, days=7):
        """ดูข้อมูลล่าสุด N วัน"""
        df = self.realtime_manager.get_realtime_data(days_back=days)
        if df.empty:
            print(f"No realtime data found for the last {days} days")
            return
        
        print(f"\n=== Realtime Data (Last {days} days) ===")
        print(df.to_string(index=False))

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Integrated Oil Price Scraper')
    parser.add_argument('--view', type=int, metavar='DAYS', 
                       help='View realtime data for the last N days')
    parser.add_argument('--summary', action='store_true',
                       help='Show realtime data summary only')
    
    args = parser.parse_args()
    
    scraper = IntegratedScraper()
    
    if args.summary:
        summary = scraper.get_realtime_summary()
        print("\n=== Realtime Data Summary ===")
        for key, value in summary.items():
            print(f"{key}: {value}")
        return
    
    if args.view:
        scraper.view_recent_data(args.view)
        return
    
    # Run all scrapers
    success = scraper.run_all_scrapers()
    
    if success:
        print("\n🎉 All scrapers completed successfully!")
        exit_code = 0
    else:
        print("\n⚠️  Some scrapers failed. Check logs for details.")
        exit_code = 1
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()