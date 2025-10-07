#!/usr/bin/env python3
"""
Airflow DAG for Oil Price Scraping - 01:00 Schedule
รัน scraper เวลา 01:00 น.
"""
from datetime import datetime, timedelta
import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import sys
import os

# เพิ่ม path สำหรับ import scraper
sys.path.append('/opt/airflow/dags')

def run_morning_scraper():
    """ฟังก์ชันสำหรับรัน scraper ตอนเช้า 01:00"""
    try:
        from scraper.combined_scraper import CombinedOilScraper
        
        scraper = CombinedOilScraper()
        success = scraper.run_complete_scraping()
        
        if not success:
            raise Exception("01:00 oil scraping failed!")
            
        print("✅ 01:00 oil scraping completed successfully!")
        return "morning_success"
        
    except Exception as e:
        print(f"❌ 01:00 oil scraping failed: {e}")
        raise

def log_morning_execution():
    """บันทึก log การรันตอน 01:00"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"� 01:00 scraping executed at: {timestamp}")
    return f"morning_executed_{timestamp}"

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

# สร้าง DAG สำหรับ 01:00
morning_dag = DAG(
    'oil_price_scraper_01h',
    default_args=default_args,
    description='Morning oil price scraping at 01:00',
    schedule_interval='0 1 * * *',  # รันทุกวันเวลา 01:00 น.
    catchup=False,
    tags=['oil-price', 'scraping', 'morning', '01h'],
)

# Tasks สำหรับ 01:00
morning_scrape_task = PythonOperator(
    task_id='morning_scrape_oil_prices',
    python_callable=run_morning_scraper,
    dag=morning_dag,
)

morning_log_task = PythonOperator(
    task_id='log_morning_execution', 
    python_callable=log_morning_execution,
    dag=morning_dag,
)

# Dependencies
morning_scrape_task >> morning_log_task
#!/usr/bin/env python3
