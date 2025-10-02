#!/usr/bin/env python3
"""
Load CSV data into PostgreSQL database
โหลดข้อมูลจากไฟล์ only_2_stations.csv เข้าสู่ฐานข้อมูล PostgreSQL
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import logging
from datetime import datetime
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CSVLoader:
    def __init__(self):
        # Database connection parameters
        self.db_config = {
            'host': 'localhost',
            'port': 5435,
            'database': 'gasohol_prediction',
            'user': 'postgres', 
            'password': 'postgres123'
        }

    def get_db_connection(self):
        """สร้างการเชื่อมต่อฐานข้อมูล"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None

    def load_csv_to_database(self, csv_path: str) -> bool:
        """โหลดข้อมูลจาก CSV เข้าฐานข้อมูล"""
        try:
            # Check if file exists
            if not os.path.exists(csv_path):
                logger.error(f"CSV file not found: {csv_path}")
                return False

            # Read CSV file
            logger.info(f"Reading CSV file: {csv_path}")
            df = pd.read_csv(csv_path)
            
            # Check required columns
            required_columns = ['Date', 'price_PTT', 'price_Shell', 'effective_date']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                return False

            # Convert date column
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            
            # Handle missing values
            df['price_PTT'] = pd.to_numeric(df['price_PTT'], errors='coerce')
            df['price_Shell'] = pd.to_numeric(df['price_Shell'], errors='coerce')
            
            # Get database connection
            conn = self.get_db_connection()
            if not conn:
                return False

            try:
                with conn.cursor() as cursor:
                    # Clear existing data
                    logger.info("Clearing existing data...")
                    cursor.execute("DELETE FROM daily_gasohol_prices")
                    
                    # Prepare data for insertion
                    data_to_insert = []
                    for _, row in df.iterrows():
                        data_to_insert.append((
                            row['Date'],
                            row['price_PTT'] if pd.notna(row['price_PTT']) else None,
                            row['price_Shell'] if pd.notna(row['price_Shell']) else None,
                            row['effective_date'] if pd.notna(row['effective_date']) else None
                        ))
                    
                    # Bulk insert data
                    logger.info(f"Inserting {len(data_to_insert)} records...")
                    execute_values(
                        cursor,
                        """
                        INSERT INTO daily_gasohol_prices (date, price_ptt, price_shell, effective_date)
                        VALUES %s
                        """,
                        data_to_insert,
                        page_size=1000
                    )
                    
                    # Commit transaction
                    conn.commit()
                    logger.info(f"Successfully loaded {len(data_to_insert)} records into database")
                    
                    # Log summary statistics
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_records,
                            MIN(date) as earliest_date,
                            MAX(date) as latest_date,
                            COUNT(CASE WHEN price_ptt IS NOT NULL THEN 1 END) as ptt_count,
                            COUNT(CASE WHEN price_shell IS NOT NULL THEN 1 END) as shell_count
                        FROM daily_gasohol_prices
                    """)
                    stats = cursor.fetchone()
                    
                    logger.info(f"Database summary:")
                    logger.info(f"  Total records: {stats[0]}")
                    logger.info(f"  Date range: {stats[1]} to {stats[2]}")
                    logger.info(f"  PTT price records: {stats[3]}")
                    logger.info(f"  Shell price records: {stats[4]}")

            finally:
                conn.close()

            return True

        except Exception as e:
            logger.error(f"Error loading CSV to database: {e}")
            return False

    def verify_data_load(self) -> bool:
        """ตรวจสอบการโหลดข้อมูล"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False

            with conn.cursor() as cursor:
                # Check total records
                cursor.execute("SELECT COUNT(*) FROM daily_gasohol_prices")
                total_count = cursor.fetchone()[0]
                
                if total_count == 0:
                    logger.error("No data found in database")
                    return False
                
                # Check recent data
                cursor.execute("""
                    SELECT date, price_ptt, price_shell, effective_date
                    FROM daily_gasohol_prices 
                    ORDER BY date DESC 
                    LIMIT 5
                """)
                recent_data = cursor.fetchall()
                
                logger.info("Recent data samples:")
                for row in recent_data:
                    logger.info(f"  {row[0]}: PTT={row[1]}, Shell={row[2]}, Effective={row[3]}")

            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error verifying data load: {e}")
            return False

def main():
    """Main function"""
    csv_path = "e:\\year4_1\\T.Boat\\programs\\perfect\\data\\only_2_stations.csv"
    
    loader = CSVLoader()
    
    logger.info("=== Starting CSV to Database Load ===")
    
    # Load CSV data
    if loader.load_csv_to_database(csv_path):
        logger.info("CSV load completed successfully")
        
        # Verify data load
        if loader.verify_data_load():
            logger.info("Data verification passed")
        else:
            logger.warning("Data verification failed")
    else:
        logger.error("CSV load failed")
        exit(1)
    
    logger.info("=== Load process completed ===")

if __name__ == "__main__":
    main()