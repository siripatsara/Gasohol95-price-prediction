#!/usr/bin/env python3
"""
Airflow DAG for Oil Price Scraping - 13:00 Schedule
รัน scraper เวลา 13:00 น. (บ่าย)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import sys
import os

import pendulum

# เพิ่ม path สำหรับ import scraper
sys.path.append('/opt/airflow/dags')

def run_afternoon_scraper():
    """ฟังก์ชันสำหรับรัน scraper ตอนบ่าย 13:00"""
    try:
        from scraper.combined_scraper import CombinedOilScraper
        
        scraper = CombinedOilScraper()
        success = scraper.run_complete_scraping()
        
        if not success:
            raise Exception("13:00 oil scraping failed!")
            
        print("✅ 13:00 oil scraping completed successfully!")
        return "afternoon_success"
        
    except Exception as e:
        print(f"❌ 13:00 oil scraping failed: {e}")
        raise

def check_daily_progress():
    """ตรวจสอบความคืบหน้าของข้อมูลในวัน"""
    try:
        import pandas as pd
        
        # อ่านข้อมูลวันนี้
        df = pd.read_csv('/opt/airflow/data/realtime_scraped_data.csv')
        today = datetime.now().date()
        today_data = df[pd.to_datetime(df['Date']).dt.date == today]
        
        if len(today_data) >= 2:
            print(f"✅ มีข้อมูล {len(today_data)} รายการสำหรับวันนี้")
            return "complete_day"
        else:
            print(f"⚠️ มีข้อมูลเพียง {len(today_data)} รายการสำหรับวันนี้")
            return "incomplete_day"
            
    except Exception as e:
        print(f"❌ Cannot check daily progress: {e}")
        return "check_failed"

def log_evening_execution():
    """บันทึก log การรันตอนเย็น"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"🌆 Evening scraping executed at: {timestamp}")
    return f"evening_executed_{timestamp}"

# Default arguments
default_args = {
    'owner': 'oil-price-team',
    'depends_on_past': False,
    'start_date': pendulum.datetime(2025, 10, 4, tz='Asia/Bangkok'),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=15),
}

# สร้าง DAG สำหรับ 13:00
afternoon_dag = DAG(
    'oil_price_scraper_13h',
    default_args=default_args,
    description='Afternoon oil price scraping at 13:00',
    schedule_interval='0 13 * * *',  # รันทุกวันเวลา 13:00 น.
    catchup=False,
    tags=['oil-price', 'scraping', 'afternoon', '13h'],
)

# Tasks สำหรับ 13:00
afternoon_scrape_task = PythonOperator(
    task_id='afternoon_scrape_oil_prices',
    python_callable=run_afternoon_scraper,
    dag=afternoon_dag,
)

daily_progress_task = PythonOperator(
    task_id='check_daily_progress',
    python_callable=check_daily_progress,
    dag=afternoon_dag,
)

afternoon_log_task = PythonOperator(
    task_id='log_afternoon_execution',
    python_callable=log_evening_execution,
    dag=afternoon_dag,
)

# Dependencies
afternoon_scrape_task >> daily_progress_task >> afternoon_log_task