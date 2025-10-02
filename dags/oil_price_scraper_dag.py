#!/usr/bin/env python3
"""
Airflow DAG for EPPO Oil Price Scraping
รัน scraper แบบตั้งเวลาทุกวันเวลา 06:00 น.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import sys
import os

# เพิ่ม path สำหรับ import scraper
sys.path.append('/opt/airflow/dags')

def run_oil_scraper():
    """ฟังก์ชันสำหรับรัน oil scraper"""
    try:
        # Import scraper (ต้องใส่ในฟังก์ชันเพื่อหลีกเลี่ยง import error ตอน DAG parsing)
        from scraper.combined_scraper import CombinedOilScraper
        
        scraper = CombinedOilScraper()
        success = scraper.run_complete_scraping()
        
        if not success:
            raise Exception("Combined oil scraping failed!")
            
        print("✅ Complete oil scraping completed successfully!")
        return "success"
        
    except Exception as e:
        print(f"❌ Combined oil scraping failed: {e}")
        raise

def check_data_quality():
    """ตรวจสอบคุณภาพข้อมูลที่ scrape มา"""
    try:
        import pandas as pd
        
        csv_path = "/opt/airflow/data/only_2_stations.csv"
        
        if not os.path.exists(csv_path):
            raise Exception(f"CSV file not found: {csv_path}")
        
        df = pd.read_csv(csv_path)
        
        # ตรวจสอบว่ามีข้อมูลล่าสุดหรือไม่
        today = datetime.now().date()
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        
        latest_date = df['Date'].max()
        
        if latest_date != today:
            print(f"⚠️ Warning: Latest data is from {latest_date}, not today ({today})")
        else:
            print(f"✅ Data quality check passed. Latest data: {latest_date}")
        
        # ตรวจสอบว่ามีราคาหรือไม่
        latest_row = df[df['Date'] == latest_date].iloc[-1]
        
        # ตรวจสอบว่ามีข้อมูลครบทุก field หรือไม่
        required_fields = ['price_PTT', 'price_Shell', 'Price_Brent', 'USD_BATH']
        missing_fields = []
        
        for field in required_fields:
            if pd.isna(latest_row.get(field)):
                missing_fields.append(field)
        
        if missing_fields:
            print(f"⚠️ Warning: Missing data fields: {', '.join(missing_fields)}")
        else:
            print(f"✅ All required data fields are complete")
        
        print(f"PTT: {latest_row.get('price_PTT')}, Shell: {latest_row.get('price_Shell')}")
        print(f"Brent Oil: ${latest_row.get('Price_Brent')}, USD/THB: {latest_row.get('USD_BATH')}")
        return "success"
        
    except Exception as e:
        print(f"❌ Data quality check failed: {e}")
        raise

# DAG configuration
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 10, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# สร้าง DAG
dag = DAG(
    'eppo_oil_price_scraper',
    default_args=default_args,
    description='Daily comprehensive oil price scraping (EPPO + Brent + USD/THB)',
    schedule_interval='0 6 * * *',  # รันทุกวันเวลา 06:00 น.
    catchup=False,
    tags=['oil-price', 'scraping', 'eppo', 'brent', 'usd-thb'],
)

# Task 1: รัน scraper
scrape_task = PythonOperator(
    task_id='scrape_oil_prices',
    python_callable=run_oil_scraper,
    dag=dag,
)

# Task 2: ตรวจสอบคุณภาพข้อมูล
quality_check_task = PythonOperator(
    task_id='check_data_quality',
    python_callable=check_data_quality,
    dag=dag,
)

# Task 3: สำรองข้อมูล (optional)
backup_task = BashOperator(
    task_id='backup_data',
    bash_command='''
    BACKUP_DIR="/opt/airflow/backups/$(date +%Y%m%d)"
    mkdir -p $BACKUP_DIR
    cp /opt/airflow/data/only_2_stations.csv $BACKUP_DIR/only_2_stations_$(date +%Y%m%d_%H%M%S).csv
    echo "Data backup completed to $BACKUP_DIR"
    ''',
    dag=dag,
)

# กำหนดลำดับการทำงาน
scrape_task >> quality_check_task >> backup_task