#!/usr/bin/env python3
"""
Airflow DAG for EPPO Oil Price Scraping
DAG สำหรับ scrape ข้อมูลราคาน้ำมันจาก EPPO แบบตั้งเวลา
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.filesystem import FileSensor
import sys
import os

# Add project path to sys.path
sys.path.append('/opt/airflow/scraper')

# Import our scraper
from eppo_oil_scraper import EPPOOilScraper

# Default arguments for the DAG
default_args = {
    'owner': 'gasohol-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 10, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'catchup': False
}

# Create DAG instance
dag = DAG(
    'eppo_oil_price_scraper',
    default_args=default_args,
    description='Daily EPPO oil price scraping and data update',
    schedule_interval='0 6,12,18 * * *',  # Run at 6 AM, 12 PM, and 6 PM daily
    max_active_runs=1,
    tags=['oil-price', 'scraping', 'gasohol']
)

def run_oil_scraper(**context):
    """ฟังก์ชันสำหรับเรียกใช้ oil scraper"""
    try:
        scraper = EPPOOilScraper()
        success = scraper.run_scraping()
        
        if not success:
            raise Exception("Oil price scraping failed")
        
        # Log execution info
        execution_date = context.get('execution_date')
        print(f"Oil scraping completed successfully at {execution_date}")
        
        return "Success"
        
    except Exception as e:
        print(f"Error in oil scraper: {e}")
        raise

def check_data_quality(**context):
    """ตรวจสอบคุณภาพข้อมูล"""
    try:
        from datetime import date
        import psycopg2
        
        # Database connection
        db_config = {
            'host': 'perfect_postgres',
            'port': 5432,
            'database': 'gasohol_prediction',
            'user': 'postgres',
            'password': 'postgres123'
        }
        
        conn = psycopg2.connect(**db_config)
        
        with conn.cursor() as cursor:
            # Check if today's data exists
            today = date.today()
            cursor.execute("""
                SELECT COUNT(*) FROM daily_gasohol_prices 
                WHERE date = %s
            """, (today,))
            
            count = cursor.fetchone()[0]
            
            if count == 0:
                raise Exception(f"No data found for {today}")
            
            # Check for valid prices
            cursor.execute("""
                SELECT price_ptt, price_shell 
                FROM daily_gasohol_prices 
                WHERE date = %s
            """, (today,))
            
            result = cursor.fetchone()
            
            if result[0] is None and result[1] is None:
                raise Exception(f"No valid prices found for {today}")
            
            print(f"Data quality check passed for {today}")
            print(f"PTT: {result[0]}, Shell: {result[1]}")
        
        conn.close()
        return "Data quality check passed"
        
    except Exception as e:
        print(f"Data quality check failed: {e}")
        raise

def log_execution_status(**context):
    """บันทึกสถานะการทำงาน"""
    try:
        import psycopg2
        from datetime import date
        
        # Database connection
        db_config = {
            'host': 'perfect_postgres',
            'port': 5432,
            'database': 'gasohol_prediction',
            'user': 'postgres',
            'password': 'postgres123'
        }
        
        conn = psycopg2.connect(**db_config)
        
        with conn.cursor() as cursor:
            execution_date = context.get('execution_date')
            
            cursor.execute("""
                INSERT INTO data_quality_logs (date, source, status, message)
                VALUES (%s, %s, %s, %s)
            """, (
                date.today(),
                'eppo_scraper',
                'success',
                f'Scraping completed successfully at {execution_date}'
            ))
            
            conn.commit()
        
        conn.close()
        print("Execution status logged successfully")
        
    except Exception as e:
        print(f"Error logging execution status: {e}")
        # Don't raise here as this is just logging

# Define tasks
scrape_oil_prices = PythonOperator(
    task_id='scrape_oil_prices',
    python_callable=run_oil_scraper,
    dag=dag,
    pool='scraping_pool'
)

check_data = PythonOperator(
    task_id='check_data_quality',
    python_callable=check_data_quality,
    dag=dag
)

log_status = PythonOperator(
    task_id='log_execution_status',
    python_callable=log_execution_status,
    dag=dag,
    trigger_rule='all_done'  # Run regardless of upstream task status
)

# Health check task
health_check = BashOperator(
    task_id='health_check',
    bash_command='echo "Starting oil price scraping pipeline..."',
    dag=dag
)

# Task dependencies
health_check >> scrape_oil_prices >> check_data >> log_status