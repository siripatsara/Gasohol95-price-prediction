#!/usr/bin/env python3
"""
Simple USD/THB Rate Provider
แหล่งข้อมูล USD/THB อย่างง่ายสำหรับกรณีที่ BOT scraper ล้มเหลว
"""

import requests
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SimpleUSDTHBProvider:
    """ดึงข้อมูล USD/THB จากแหล่งข้อมูลอื่น"""
    
    def __init__(self):
        self.sources = [
            self.get_from_exchangerate_api,
            self.get_from_fixer,
            self.get_from_xe_com,
            self.get_from_static_estimate
        ]
    
    def get_usd_thb_rate(self) -> float:
        """ดึงอัตราแลกเปลี่ยน USD/THB จากแหล่งต่างๆ"""
        for source in self.sources:
            try:
                rate = source()
                if rate and 30.0 <= rate <= 40.0:  # Reasonable range check
                    logger.info(f"USD/THB rate obtained: {rate} from {source.__name__}")
                    return rate
            except Exception as e:
                logger.warning(f"Failed to get USD/THB from {source.__name__}: {e}")
                continue
        
        # Ultimate fallback - educated guess based on recent trends
        fallback_rate = 32.2014
        logger.warning(f"All USD/THB sources failed, using fallback: {fallback_rate}")
        return fallback_rate
    
    def get_from_exchangerate_api(self) -> float:
        """ดึงจาก exchangerate-api.com (free tier)"""
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data['rates']['THB'])
    
    def get_from_fixer(self) -> float:
        """ดึงจาก fixer.io (สำหรับกรณีมี API key)"""
        # This would need API key - skip for now
        raise Exception("Fixer.io requires API key")
    
    def get_from_xe_com(self) -> float:
        """ดึงจาก xe.com (HTML scraping)"""
        url = "https://www.xe.com/currencyconverter/convert/?Amount=1&From=USD&To=THB"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Simple regex to find rate
        import re
        pattern = r'(\d+\.\d+)\s+Thai\s+Baht'
        match = re.search(pattern, response.text)
        if match:
            return float(match.group(1))
        
        raise Exception("Could not parse XE.com rate")
    
    def get_from_static_estimate(self) -> float:
        """ใช้การประมาณจากข้อมูลล่าสุดที่รู้"""
        # อ้างอิงจากข้อมูล BOT ล่าสุดที่เรารู้
        # 06 Oct 2025: 32.1449 (Buying Rates Sight Bill)
        # 03 Oct 2025: 32.2014 
        
        # สมมติว่าอัตราจะไม่เปลี่ยนแปลงมากในระยะสั้น
        estimated_rate = 32.1449  # ใช้ค่าล่าสุดจาก BOT
        logger.info(f"Using estimated USD/THB rate: {estimated_rate}")
        return estimated_rate

# Integrate ใน eppo_oil_scraper.py
def get_backup_usd_rate() -> float:
    """Function ที่ใช้เรียกจาก eppo_oil_scraper.py"""
    provider = SimpleUSDTHBProvider()
    return provider.get_usd_thb_rate()

if __name__ == "__main__":
    # Test the provider
    logging.basicConfig(level=logging.INFO)
    provider = SimpleUSDTHBProvider()
    rate = provider.get_usd_thb_rate()
    print(f"USD/THB Rate: {rate}")