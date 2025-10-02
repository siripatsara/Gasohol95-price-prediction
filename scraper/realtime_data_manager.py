#!/usr/bin/env python3
"""
Real-time Data Manager
จัดการข้อมูลที่ scrape แบบ real-time ตั้งแต่วันที่เริ่มต้นระบบ
"""

import os
import sys
import pandas as pd
import logging
from datetime import datetime, date
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/realtime_data_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RealtimeDataManager:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"
        
        # ไฟล์ข้อมูลหลัก (มีข้อมูลเก่าด้วย)
        self.main_csv = self.data_dir / "only_2_stations.csv"
        
        # ไฟล์ข้อมูล real-time (เฉพาะข้อมูลที่ scrape ใหม่)
        self.realtime_csv = self.data_dir / "realtime_scraped_data.csv"
        
        # วันที่เริ่มต้นระบบ real-time
        self.start_date = date(2025, 10, 3)  # เริ่มต้นวันนี้
        
        # Create realtime file if not exists
        self.init_realtime_file()
    
    def init_realtime_file(self):
        """สร้างไฟล์ real-time หากยังไม่มี"""
        try:
            if not self.realtime_csv.exists():
                # สร้างไฟล์ว่างด้วย header เดียวกับไฟล์หลัก
                if self.main_csv.exists():
                    main_df = pd.read_csv(self.main_csv, nrows=0)  # อ่านเฉพาะ header
                    main_df.to_csv(self.realtime_csv, index=False)
                    logger.info(f"Created realtime file: {self.realtime_csv}")
                else:
                    # สร้าง header ตามโครงสร้างที่คาดหวัง
                    columns = ['Date', 'price_PTT', 'price_Shell', 'effective_date', 'Price_Brent', 'USD_BATH', 'Price_Levy']
                    empty_df = pd.DataFrame(columns=columns)
                    empty_df.to_csv(self.realtime_csv, index=False)
                    logger.info(f"Created realtime file with default headers: {self.realtime_csv}")
            else:
                logger.info(f"Realtime file already exists: {self.realtime_csv}")
                
        except Exception as e:
            logger.error(f"Failed to initialize realtime file: {e}")
    
    def get_realtime_data(self, days_back=None):
        """อ่านข้อมูล real-time"""
        try:
            if not self.realtime_csv.exists():
                logger.warning("Realtime file does not exist")
                return pd.DataFrame()
            
            df = pd.read_csv(self.realtime_csv)
            if df.empty:
                return df
                
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            
            # กรองข้อมูลตามจำนวนวันที่ต้องการ
            if days_back:
                cutoff_date = datetime.now().date() - pd.Timedelta(days=days_back).to_pytimedelta()
                df = df[df['Date'] >= cutoff_date]
            
            return df.sort_values('Date')
            
        except Exception as e:
            logger.error(f"Failed to read realtime data: {e}")
            return pd.DataFrame()
    
    def add_realtime_data(self, date_str, **data):
        """เพิ่มข้อมูลใหม่ลงไฟล์ real-time"""
        try:
            # แปลง date string เป็น date object
            if isinstance(date_str, str):
                scrape_date = pd.to_datetime(date_str).date()
            else:
                scrape_date = date_str
            
            # ตรวจสอบว่าเป็นข้อมูลหลังวันที่เริ่มระบบหรือไม่
            if scrape_date < self.start_date:
                logger.info(f"Date {scrape_date} is before system start date {self.start_date} - not adding to realtime file")
                return True
            
            # อ่านข้อมูลที่มีอยู่
            df = self.get_realtime_data()
            
            # เตรียมข้อมูลใหม่
            new_row = {'Date': scrape_date}
            new_row.update(data)
            
            # ตรวจสอบว่ามีข้อมูลวันนี้อยู่แล้วหรือไม่
            existing_mask = df['Date'] == scrape_date
            
            if existing_mask.any():
                # อัพเดตข้อมูลที่มีอยู่
                for col, value in new_row.items():
                    if col in df.columns and pd.notna(value):
                        df.loc[existing_mask, col] = value
                logger.info(f"Updated realtime data for {scrape_date}")
            else:
                # เพิ่มข้อมูลใหม่
                new_df = pd.DataFrame([new_row])
                df = pd.concat([df, new_df], ignore_index=True)
                logger.info(f"Added new realtime data for {scrape_date}")
            
            # เรียงลำดับตามวันที่และบันทึก
            df = df.sort_values('Date').reset_index(drop=True)
            df.to_csv(self.realtime_csv, index=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add realtime data: {e}")
            return False
    
    def sync_from_main_file(self, start_date=None):
        """ดึงข้อมูลจากไฟล์หลักมาใส่ในไฟล์ real-time (สำหรับข้อมูลหลังวันที่กำหนด)"""
        try:
            if not self.main_csv.exists():
                logger.warning("Main CSV file does not exist")
                return False
            
            # ใช้วันที่เริ่มระบบเป็นค่าเริ่มต้น
            sync_start_date = start_date or self.start_date
            
            # อ่านข้อมูลจากไฟล์หลัก
            main_df = pd.read_csv(self.main_csv)
            main_df['Date'] = pd.to_datetime(main_df['Date']).dt.date
            
            # กรองข้อมูลตั้งแต่วันที่เริ่มระบบ
            recent_data = main_df[main_df['Date'] >= sync_start_date]
            
            if recent_data.empty:
                logger.info(f"No data found in main file from {sync_start_date}")
                return True
            
            # เพิ่มข้อมูลแต่ละแถวลงไฟล์ real-time
            for _, row in recent_data.iterrows():
                row_data = row.to_dict()
                date_val = row_data.pop('Date')
                self.add_realtime_data(date_val, **row_data)
            
            logger.info(f"Synced {len(recent_data)} rows from main file to realtime file")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync from main file: {e}")
            return False
    
    def get_summary(self):
        """สรุปข้อมูลใน real-time file"""
        try:
            df = self.get_realtime_data()
            
            if df.empty:
                return {
                    'total_records': 0,
                    'date_range': 'No data',
                    'latest_date': 'No data',
                    'columns': []
                }
            
            summary = {
                'total_records': len(df),
                'date_range': f"{df['Date'].min()} to {df['Date'].max()}",
                'latest_date': df['Date'].max(),
                'columns': df.columns.tolist(),
                'latest_record': df.iloc[-1].to_dict() if not df.empty else {}
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return {'error': str(e)}

def main():
    """ทดสอบ RealtimeDataManager"""
    manager = RealtimeDataManager()
    
    # แสดงสรุปข้อมูล
    summary = manager.get_summary()
    print("\n=== Realtime Data Summary ===")
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    # ซิงค์ข้อมูลจากไฟล์หลัก
    print("\n=== Syncing from main file ===")
    success = manager.sync_from_main_file()
    if success:
        print("✅ Sync completed successfully")
        
        # แสดงสรุปใหม่
        summary = manager.get_summary()
        print("\n=== Updated Summary ===")
        for key, value in summary.items():
            print(f"{key}: {value}")
    else:
        print("❌ Sync failed")

if __name__ == "__main__":
    main()