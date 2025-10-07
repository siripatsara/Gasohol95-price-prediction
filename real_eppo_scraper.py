#!/usr/bin/env python3
"""
Mock EPPO Oil Scraper for afternoon check testing
ใช้สำหรับทดสอบ afternoon_smart_check แบบ standalone
"""

import requests
from datetime import datetime, timedelta
import logging
import time

logger = logging.getLogger(__name__)

class EPPOOilScraperNoDB:
    """Mock EPPO Oil Scraper ที่ไม่ต้องเชื่อมต่อ database"""
    
    def __init__(self):
        self.base_url = "https://www.eppo.go.th"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def test_connection(self):
        """ทดสอบการเชื่อมต่อเว็บไซต์"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def scrape_oil_prices(self):
        """สร้างข้อมูลจำลองสำหรับทดสอบ afternoon check"""
        current_time = datetime.now()
        
        # สร้างข้อมูลจำลองที่แตกต่างจากข้อมูลเดิม
        mock_data = {
            'date': current_time,
            'price_ptt': 32.15,  # เปลี่ยนจาก 32.10 (เพิ่ม 0.05)
            'price_shell': 32.65,  # เปลี่ยนจาก 32.60 (เพิ่ม 0.05)
            'effective_date': '6 Oct 05:00',  # เปลี่ยนจาก '3 Oct 05:00'
            'scraping_time': current_time.isoformat(),
            'success': True
        }
        
        logger.info(f"Mock scraping completed: {mock_data}")
        return mock_data
    
    def get_usd_thb_rate(self):
        """สร้างอัตราแลกเปลี่ยน USD/THB จำลอง"""
        # ใช้อัตราล่าสุดจากเว็บไซต์ BOT (6 Oct 2025)
        return 32.5528
    
    def get_brent_oil_price(self):
        """สร้างราคาน้ำมัน Brent จำลอง"""
        return 66.87
    
    def get_latest_data_from_db(self):
        """สร้างข้อมูลล่าสุดจาก database แบบจำลอง"""
        # ข้อมูลเก่าจาก database (3 Oct)
        return {
            'price_ptt': 32.10,
            'price_shell': 32.60,
            'effective_date': '3 Oct 05:00',
            'usd_bath': 32.6137,  # อัตราเก่าจาก 3 Oct
            'price_brent': 66.50,
            'date': datetime.now() - timedelta(days=3)
        }