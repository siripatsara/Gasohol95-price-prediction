#!/usr/bin/env python3
"""
CSV to PostgreSQL Sync Script
ซิงค์ข้อมูลจาก only_2_stations.csv ไป PostgreSQL
"""

import pandas as pd
import psycopg2
from datetime import datetime
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CSVToPostgreSync:
    def __init__(self):
        """Initialize PostgreSQL connection"""
        self.db_config = {
            'host': 'localhost',
            'port': 5435,
            'database': 'gasohol_prediction',
            'user': 'postgres',
            'password': 'postgres123'
        }
        self.csv_file = 'E:/year4_1/T.Boat/programs/perfect/data/only_2_stations.csv'
        
    def connect_db(self):
        """เชื่อมต่อ PostgreSQL"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return None
    
    def create_oil_prices_table(self):
        """สร้าง table สำหรับข้อมูลน้ำมัน"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS oil_prices_realtime (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            price_ptt DECIMAL(6,2),
            price_shell DECIMAL(6,2), 
            effective_date VARCHAR(50),
            price_brent DECIMAL(8,2),
            usd_bath DECIMAL(8,4),
            price_levy DECIMAL(6,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date)
        );
        """
        
        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(create_table_sql)
                conn.commit()
                logger.info("✅ Table oil_prices_realtime created/verified")
                cursor.close()
                conn.close()
                return True
            except Exception as e:
                logger.error(f"Failed to create table: {e}")
                conn.close()
                return False
        return False
    
    def load_csv_data(self):
        """โหลดข้อมูลจาก CSV"""
        try:
            if not os.path.exists(self.csv_file):
                logger.error(f"CSV file not found: {self.csv_file}")
                return None
                
            df = pd.read_csv(self.csv_file)
            logger.info(f"✅ Loaded {len(df)} records from CSV")
            return df
        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            return None
    
    def sync_data(self):
        """ซิงค์ข้อมูลจาก CSV ไป PostgreSQL"""
        # Create table first
        if not self.create_oil_prices_table():
            return False
            
        # Load CSV data
        df = self.load_csv_data()
        if df is None:
            return False
        
        conn = self.connect_db()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            
            # Prepare data for insertion
            insert_sql = """
            INSERT INTO oil_prices_realtime 
            (date, price_ptt, price_shell, effective_date, price_brent, usd_bath, price_levy)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date) 
            DO UPDATE SET
                price_ptt = EXCLUDED.price_ptt,
                price_shell = EXCLUDED.price_shell,
                effective_date = EXCLUDED.effective_date,
                price_brent = EXCLUDED.price_brent,
                usd_bath = EXCLUDED.usd_bath,
                price_levy = EXCLUDED.price_levy,
                updated_at = CURRENT_TIMESTAMP
            """
            
            # Convert data and insert
            inserted_count = 0
            updated_count = 0
            
            for _, row in df.iterrows():
                try:
                    # Parse date
                    date_val = pd.to_datetime(row['Date']).date()
                    
                    # Check if record exists
                    cursor.execute("SELECT id FROM oil_prices_realtime WHERE date = %s", (date_val,))
                    exists = cursor.fetchone()
                    
                    # Insert or update
                    cursor.execute(insert_sql, (
                        date_val,
                        float(row['price_PTT']) if pd.notna(row['price_PTT']) else None,
                        float(row['price_Shell']) if pd.notna(row['price_Shell']) else None,
                        str(row['effective_date']) if pd.notna(row['effective_date']) else None,
                        float(row['Price_Brent']) if pd.notna(row['Price_Brent']) else None,
                        float(row['USD_BATH']) if pd.notna(row['USD_BATH']) else None,
                        float(row['Price_Levy']) if pd.notna(row['Price_Levy']) else None
                    ))
                    
                    if exists:
                        updated_count += 1
                    else:
                        inserted_count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to process row {row.name}: {e}")
                    continue
            
            conn.commit()
            logger.info(f"✅ Sync completed: {inserted_count} inserted, {updated_count} updated")
            
            # Log quality info
            self.log_sync_quality(cursor, len(df), inserted_count + updated_count)
            conn.commit()
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            conn.rollback()
            conn.close()
            return False
    
    def log_sync_quality(self, cursor, total_csv, total_synced):
        """บันทึกคุณภาพการ sync"""
        quality_score = (total_synced / total_csv) * 100 if total_csv > 0 else 0
        
        log_sql = """
        INSERT INTO data_quality_logs (date, source, status, message, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        cursor.execute(log_sql, (
            datetime.now().date(),
            'CSV_SYNC',
            'SUCCESS' if quality_score > 95 else 'WARNING',
            f'Synced {total_synced}/{total_csv} records ({quality_score:.1f}%)',
            datetime.now()
        ))
    
    def get_latest_data(self, limit=10):
        """ดูข้อมูลล่าสุดที่ sync แล้ว"""
        conn = self.connect_db()
        if not conn:
            return None
            
        try:
            query = """
            SELECT date, price_ptt, price_shell, price_brent, usd_bath, price_levy, updated_at
            FROM oil_prices_realtime 
            ORDER BY date DESC 
            LIMIT %s
            """
            
            df = pd.read_sql(query, conn, params=[limit])
            conn.close()
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            conn.close()
            return None

if __name__ == "__main__":
    syncer = CSVToPostgreSync()
    
    print("🔄 Starting CSV to PostgreSQL sync...")
    success = syncer.sync_data()
    
    if success:
        print("\n📊 Latest synced data:")
        latest_data = syncer.get_latest_data(5)
        if latest_data is not None:
            print(latest_data.to_string(index=False))
        
        print(f"\n✅ Sync completed successfully!")
        print("💡 Data is now available in PostgreSQL for real-time analytics")
    else:
        print("❌ Sync failed. Check logs for details.")