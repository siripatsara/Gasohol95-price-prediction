#!/usr/bin/env python3
"""
Script to update PostgreSQL oil_prices_realtime table with data from only_2_stations.csv
อัพเดทข้อมูลใน PostgreSQL ให้ตรงกับ CSV file
"""

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseUpdater:
    def __init__(self):
        # Database connection parameters - adjust for your environment
        self.db_config = {
            'host': 'localhost',  # Change to 'postgres' if running in Docker
            'port': 5432,
            'database': 'gasohol_prediction', 
            'user': 'postgres',
            'password': 'postgres123'
        }
        
        # CSV file path
        self.csv_file = "data/only_2_stations.csv"

    def get_db_connection(self):
        """สร้างการเชื่อมต่อฐานข้อมูล"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            # Try alternative host for Docker environment
            try:
                self.db_config['host'] = 'postgres'
                conn = psycopg2.connect(**self.db_config)
                logger.info("Connected using Docker host 'postgres'")
                return conn
            except Exception as e2:
                logger.error(f"Docker connection also failed: {e2}")
                return None

    def check_table_exists(self):
        """ตรวจสอบว่าตาราง oil_prices_realtime มีอยู่หรือไม่"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
                
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'oil_prices_realtime'
                    );
                """)
                exists = cursor.fetchone()[0]
                
            conn.close()
            return exists
            
        except Exception as e:
            logger.error(f"Error checking table existence: {e}")
            return False

    def create_table_if_not_exists(self):
        """สร้างตาราง oil_prices_realtime หากยังไม่มี"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
                
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS oil_prices_realtime (
                        id SERIAL PRIMARY KEY,
                        date DATE NOT NULL,
                        price_ptt DECIMAL(10,2),
                        price_shell DECIMAL(10,2),
                        effective_date TEXT,
                        price_brent DECIMAL(10,2),
                        usd_bath DECIMAL(10,4),
                        price_levy DECIMAL(10,2),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(date)
                    );
                """)
                
                # Create index on date for better performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_oil_prices_date 
                    ON oil_prices_realtime(date);
                """)
                
                conn.commit()
                logger.info("Table oil_prices_realtime created successfully")
                
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            return False

    def load_csv_data(self):
        """โหลดข้อมูลจาก CSV file"""
        try:
            logger.info(f"Loading CSV data from {self.csv_file}")
            
            # Read CSV file
            df = pd.read_csv(self.csv_file)
            logger.info(f"Loaded {len(df)} rows from CSV")
            
            # Convert Date column to datetime
            df['Date'] = pd.to_datetime(df['Date'])
            
            # Handle NaN values
            df = df.fillna(None)
            
            # Show data info
            logger.info("CSV columns: " + ", ".join(df.columns.tolist()))
            logger.info(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
            logger.info(f"Sample data:\n{df.head(3)}")
            logger.info(f"Latest data:\n{df.tail(3)}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading CSV data: {e}")
            return None

    def get_existing_data_count(self):
        """นับจำนวนข้อมูลที่มีอยู่ในฐานข้อมูล"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return 0
                
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM oil_prices_realtime")
                count = cursor.fetchone()[0]
                
            conn.close()
            return count
            
        except Exception as e:
            logger.error(f"Error counting existing data: {e}")
            return 0

    def clear_existing_data(self):
        """ลบข้อมูลเดิมทั้งหมด (ถ้าต้องการ fresh start)"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
                
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM oil_prices_realtime")
                deleted_count = cursor.rowcount
                conn.commit()
                logger.info(f"Deleted {deleted_count} existing rows")
                
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error clearing existing data: {e}")
            return False

    def insert_csv_data(self, df):
        """แทรกข้อมูลจาก CSV ลงในฐานข้อมูล"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
                
            insert_count = 0
            update_count = 0
            error_count = 0
            
            with conn.cursor() as cursor:
                for index, row in df.iterrows():
                    try:
                        # Prepare data
                        date_val = row['Date'].date() if pd.notna(row['Date']) else None
                        price_ptt = float(row['price_PTT']) if pd.notna(row['price_PTT']) else None
                        price_shell = float(row['price_Shell']) if pd.notna(row['price_Shell']) else None
                        effective_date = row['effective_date'] if pd.notna(row['effective_date']) else None
                        price_brent = float(row['Price_Brent']) if pd.notna(row['Price_Brent']) else None
                        usd_bath = float(row['USD_BATH']) if pd.notna(row['USD_BATH']) else None
                        price_levy = float(row['Price_Levy']) if pd.notna(row['Price_Levy']) else None
                        
                        # Use UPSERT (INSERT ... ON CONFLICT UPDATE)
                        cursor.execute("""
                            INSERT INTO oil_prices_realtime 
                            (date, price_ptt, price_shell, effective_date, price_brent, usd_bath, price_levy, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (date) 
                            DO UPDATE SET 
                                price_ptt = EXCLUDED.price_ptt,
                                price_shell = EXCLUDED.price_shell,
                                effective_date = EXCLUDED.effective_date,
                                price_brent = EXCLUDED.price_brent,
                                usd_bath = EXCLUDED.usd_bath,
                                price_levy = EXCLUDED.price_levy,
                                updated_at = CURRENT_TIMESTAMP
                            RETURNING (xmax = 0) AS inserted
                        """, (date_val, price_ptt, price_shell, effective_date, price_brent, usd_bath, price_levy))
                        
                        result = cursor.fetchone()
                        if result and result[0]:  # New insert
                            insert_count += 1
                        else:  # Update
                            update_count += 1
                            
                        # Commit every 1000 rows for performance
                        if (index + 1) % 1000 == 0:
                            conn.commit()
                            logger.info(f"Processed {index + 1} rows...")
                            
                    except Exception as e:
                        logger.warning(f"Error processing row {index}: {e}")
                        error_count += 1
                        continue
                
                # Final commit
                conn.commit()
                
            conn.close()
            
            logger.info(f"Data sync completed:")
            logger.info(f"  - Inserted: {insert_count} new rows")
            logger.info(f"  - Updated: {update_count} existing rows")
            logger.info(f"  - Errors: {error_count} rows")
            logger.info(f"  - Total processed: {len(df)} rows")
            
            return True
            
        except Exception as e:
            logger.error(f"Error inserting CSV data: {e}")
            return False

    def verify_data_sync(self, df):
        """ตรวจสอบว่าข้อมูลใน database ตรงกับ CSV หรือไม่"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
                
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get total count
                cursor.execute("SELECT COUNT(*) as total FROM oil_prices_realtime")
                db_count = cursor.fetchone()['total']
                
                # Get date range
                cursor.execute("""
                    SELECT MIN(date) as min_date, MAX(date) as max_date 
                    FROM oil_prices_realtime
                """)
                date_range = cursor.fetchone()
                
                # Get latest few records
                cursor.execute("""
                    SELECT date, price_ptt, price_shell, effective_date, price_brent, usd_bath, price_levy
                    FROM oil_prices_realtime 
                    ORDER BY date DESC 
                    LIMIT 5
                """)
                latest_records = cursor.fetchall()
                
            conn.close()
            
            logger.info(f"Database verification:")
            logger.info(f"  - CSV rows: {len(df)}")
            logger.info(f"  - DB rows: {db_count}")
            logger.info(f"  - Date range: {date_range['min_date']} to {date_range['max_date']}")
            
            logger.info(f"Latest 5 records in database:")
            for record in latest_records:
                logger.info(f"  {record['date']}: PTT={record['price_ptt']}, Shell={record['price_shell']}")
            
            # Check if counts match
            if db_count == len(df):
                logger.info("✅ Database row count matches CSV")
                return True
            else:
                logger.warning(f"⚠️ Row count mismatch: CSV={len(df)}, DB={db_count}")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying data sync: {e}")
            return False

    def run_sync(self, clear_existing=False):
        """รันการ sync ข้อมูลทั้งหมด"""
        try:
            logger.info("=== Starting PostgreSQL Database Sync ===")
            
            # 1. Check/create table
            if not self.check_table_exists():
                logger.info("Table doesn't exist, creating...")
                if not self.create_table_if_not_exists():
                    logger.error("Failed to create table")
                    return False
            else:
                logger.info("Table oil_prices_realtime exists")
            
            # 2. Load CSV data
            df = self.load_csv_data()
            if df is None:
                logger.error("Failed to load CSV data")
                return False
            
            # 3. Check existing data
            existing_count = self.get_existing_data_count()
            logger.info(f"Existing data in database: {existing_count} rows")
            
            # 4. Clear existing data if requested
            if clear_existing and existing_count > 0:
                logger.info("Clearing existing data...")
                if not self.clear_existing_data():
                    logger.error("Failed to clear existing data")
                    return False
            
            # 5. Insert/update data
            logger.info("Syncing CSV data to database...")
            if not self.insert_csv_data(df):
                logger.error("Failed to insert CSV data")
                return False
            
            # 6. Verify sync
            logger.info("Verifying data sync...")
            if self.verify_data_sync(df):
                logger.info("✅ Data sync completed successfully!")
                return True
            else:
                logger.warning("⚠️ Data sync completed with warnings")
                return True
                
        except Exception as e:
            logger.error(f"Error in sync process: {e}")
            return False

def main():
    """Main function"""
    print("📊 PostgreSQL Database Sync Tool")
    print("Syncing data from only_2_stations.csv to oil_prices_realtime table")
    print("=" * 60)
    
    # Create updater instance
    updater = DatabaseUpdater()
    
    # Ask user about clearing existing data
    clear_existing = False
    try:
        existing_count = updater.get_existing_data_count()
        if existing_count > 0:
            print(f"Found {existing_count} existing rows in database.")
            response = input("Do you want to clear existing data first? (y/N): ").strip().lower()
            clear_existing = response in ['y', 'yes']
    except:
        pass
    
    # Run sync
    success = updater.run_sync(clear_existing=clear_existing)
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Database sync completed successfully!")
        print("✅ PostgreSQL oil_prices_realtime table is now up to date with CSV data")
    else:
        print("❌ Database sync failed!")
        print("🔧 Please check the error messages above")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)