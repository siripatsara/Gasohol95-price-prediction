#!/usr/bin/env python3
"""
Test script for EPPO Oil Scraper
สคริปต์ทดสอบการทำงานของ scraper
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.eppo_oil_scraper import EPPOOilScraper
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_scraper():
    """ทดสอบการทำงานของ scraper"""
    print("=== Testing EPPO Oil Scraper ===\n")
    
    # Initialize scraper
    scraper = EPPOOilScraper()
    
    print("1. Testing web scraping...")
    scraped_data = scraper.scrape_oil_prices()
    
    if scraped_data:
        print("✅ Web scraping successful!")
        print(f"   Date: {scraped_data['date']}")
        print(f"   PTT Price: {scraped_data['price_ptt']}")
        print(f"   Shell Price: {scraped_data['price_shell']}")
        print(f"   Effective Date: {scraped_data.get('effective_date', 'N/A')}")
    else:
        print("❌ Web scraping failed!")
        return False
    
    print("\n2. Testing database connection...")
    conn = scraper.get_db_connection()
    if conn:
        print("✅ Database connection successful!")
        conn.close()
    else:
        print("❌ Database connection failed!")
        print("   Make sure PostgreSQL is running on port 5435")
        return False
    
    print("\n3. Testing full scraping process...")
    success = scraper.run_scraping()
    
    if success:
        print("✅ Full scraping process successful!")
    else:
        print("❌ Full scraping process failed!")
        return False
    
    print("\n=== All tests passed! ===")
    return True

def main():
    """Main function"""
    try:
        success = test_scraper()
        if not success:
            sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()