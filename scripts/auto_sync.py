#!/usr/bin/env python3
"""
Auto-sync Smart Oil Scraper to PostgreSQL
ให้ Smart Oil Scraper เขียนข้อมูลไป PostgreSQL อัตโนมัติ
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from csv_to_postgres_sync import CSVToPostgreSync
import logging

def auto_sync_after_scraping():
    """รันหลังจาก Smart Oil Scraper เสร็จ"""
    logger = logging.getLogger(__name__)
    
    try:
        syncer = CSVToPostgreSync()
        success = syncer.sync_data()
        
        if success:
            logger.info("✅ Auto-sync to PostgreSQL completed")
            return True
        else:
            logger.error("❌ Auto-sync failed")
            return False
            
    except Exception as e:
        logger.error(f"Auto-sync error: {e}")
        return False

if __name__ == "__main__":
    auto_sync_after_scraping()