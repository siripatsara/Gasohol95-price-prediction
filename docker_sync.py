#!/usr/bin/env python3
"""
Easy script to sync CSV data to PostgreSQL using Docker
รัน PostgreSQL ใน Docker และ sync ข้อมูลจาก CSV
"""

import subprocess
import time
import sys
import os
import psycopg2
import pandas as pd
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command, description=""):
    """รันคำสั่งและแสดงผล"""
    if description:
        logger.info(f"{description}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✅ Success: {command}")
            if result.stdout:
                logger.info(f"Output: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"❌ Failed: {command}")
            logger.error(f"Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        logger.error(f"❌ Exception running command: {e}")
        return False

def check_docker():
    """ตรวจสอบว่า Docker ติดตั้งและรันอยู่หรือไม่"""
    logger.info("Checking Docker installation...")
    return run_command("docker --version", "Checking Docker version")

def start_postgres_container():
    """เริ่ม PostgreSQL container"""
    logger.info("Starting PostgreSQL container...")
    
    # Stop existing container if running
    run_command("docker stop postgres-oil", "Stopping existing container (if any)")
    run_command("docker rm postgres-oil", "Removing existing container (if any)")
    
    # Start new container
    command = """docker run --name postgres-oil \
  -e POSTGRES_DB=gasohol_prediction \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres123 \
  -p 5432:5432 \
  -d postgres:13"""
  
    if run_command(command, "Starting PostgreSQL container"):
        logger.info("✅ PostgreSQL container started successfully")
        logger.info("⏳ Waiting for PostgreSQL to initialize...")
        time.sleep(10)  # Wait for PostgreSQL to be ready
        return True
    else:
        logger.error("❌ Failed to start PostgreSQL container")
        return False

def test_connection():
    """ทดสอบการเชื่อมต่อ PostgreSQL"""
    logger.info("Testing PostgreSQL connection...")
    
    max_retries = 5
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='gasohol_prediction',
                user='postgres',
                password='postgres123'
            )
            conn.close()
            logger.info("✅ PostgreSQL connection successful!")
            return True
        except Exception as e:
            if i < max_retries - 1:
                logger.warning(f"Connection attempt {i+1} failed: {e}")
                logger.info("⏳ Retrying in 5 seconds...")
                time.sleep(5)
            else:
                logger.error(f"❌ All connection attempts failed: {e}")
                return False

def sync_data():
    """Sync CSV data to PostgreSQL"""
    logger.info("Starting data sync...")
    
    try:
        # Load CSV data
        csv_file = "data/only_2_stations.csv"
        logger.info(f"Loading data from {csv_file}...")
        df = pd.read_csv(csv_file)
        logger.info(f"Loaded {len(df)} rows from CSV")
        
        # Connect to database
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='gasohol_prediction',
            user='postgres',
            password='postgres123'
        )
        
        # Create table
        logger.info("Creating table...")
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
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_oil_prices_date 
                ON oil_prices_realtime(date);
            """)
            
            conn.commit()
            logger.info("✅ Table created successfully")
        
        # Insert data in batches
        logger.info("Inserting data...")
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.fillna(None)
        
        insert_count = 0
        update_count = 0
        
        with conn.cursor() as cursor:
            for index, row in df.iterrows():
                try:
                    date_val = row['Date'].date()
                    price_ptt = float(row['price_PTT']) if pd.notna(row['price_PTT']) else None
                    price_shell = float(row['price_Shell']) if pd.notna(row['price_Shell']) else None
                    effective_date = row['effective_date'] if pd.notna(row['effective_date']) else None
                    price_brent = float(row['Price_Brent']) if pd.notna(row['Price_Brent']) else None
                    usd_bath = float(row['USD_BATH']) if pd.notna(row['USD_BATH']) else None
                    price_levy = float(row['Price_Levy']) if pd.notna(row['Price_Levy']) else None
                    
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
                    if result and result[0]:
                        insert_count += 1
                    else:
                        update_count += 1
                    
                    if (index + 1) % 500 == 0:
                        conn.commit()
                        logger.info(f"Processed {index + 1}/{len(df)} rows...")
                        
                except Exception as e:
                    logger.warning(f"Error processing row {index}: {e}")
                    continue
            
            conn.commit()
        
        # Verify results
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM oil_prices_realtime")
            total_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(date), MAX(date) FROM oil_prices_realtime")
            date_range = cursor.fetchone()
            
            cursor.execute("""
                SELECT date, price_ptt, price_shell, effective_date 
                FROM oil_prices_realtime 
                ORDER BY date DESC 
                LIMIT 5
            """)
            latest_rows = cursor.fetchall()
        
        conn.close()
        
        logger.info("🎉 Data sync completed successfully!")
        logger.info(f"📊 Results:")
        logger.info(f"  - Total rows in database: {total_count}")
        logger.info(f"  - New inserts: {insert_count}")
        logger.info(f"  - Updates: {update_count}")
        logger.info(f"  - Date range: {date_range[0]} to {date_range[1]}")
        
        logger.info(f"📈 Latest 5 records:")
        for row in latest_rows:
            logger.info(f"  {row[0]}: PTT={row[1]}, Shell={row[2]}")
        
        # Verify Shell price fix
        latest_shell = latest_rows[0][2] if latest_rows else None
        if latest_shell == 32.65:
            logger.info("✅ Shell price fix verified: 32.65 in database!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Data sync failed: {e}")
        return False

def main():
    """Main function"""
    print("🚀 PostgreSQL Docker Setup & Data Sync")
    print("=" * 50)
    
    # Check prerequisites
    if not check_docker():
        print("❌ Docker is not available. Please install Docker first.")
        return False
    
    if not os.path.exists("data/only_2_stations.csv"):
        print("❌ CSV file not found: data/only_2_stations.csv")
        return False
    
    # Ask user what to do
    print("\nChoose an option:")
    print("1. Start PostgreSQL container and sync data (full setup)")
    print("2. Only sync data (PostgreSQL already running)")
    print("3. Only start PostgreSQL container")
    
    try:
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            # Full setup
            if not start_postgres_container():
                return False
            
            if not test_connection():
                return False
            
            if not sync_data():
                return False
            
            print("\n🎉 Complete setup finished!")
            print("✅ PostgreSQL container running")
            print("✅ Data synced successfully")
            print(f"📝 Database URL: postgresql://postgres:postgres123@localhost:5432/gasohol_prediction")
            
        elif choice == "2":
            # Only sync data
            if not test_connection():
                print("❌ Cannot connect to PostgreSQL. Make sure it's running.")
                return False
            
            if not sync_data():
                return False
            
            print("\n✅ Data sync completed!")
            
        elif choice == "3":
            # Only start container
            if not start_postgres_container():
                return False
            
            if not test_connection():
                return False
            
            print("\n✅ PostgreSQL container started!")
            print(f"📝 Database URL: postgresql://postgres:postgres123@localhost:5432/gasohol_prediction")
            
        else:
            print("❌ Invalid choice")
            return False
        
        print("\n📋 Useful commands:")
        print("Connect to database: docker exec -it postgres-oil psql -U postgres -d gasohol_prediction")
        print("Stop container: docker stop postgres-oil")
        print("View logs: docker logs postgres-oil")
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)