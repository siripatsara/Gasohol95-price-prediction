#!/usr/bin/env python3
"""
Alternative script to generate SQL statements for updating PostgreSQL
สร้าง SQL statements เพื่ออัพเดท oil_prices_realtime table
"""

import pandas as pd
import logging
from datetime import datetime
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_sql_statements():
    """สร้าง SQL statements สำหรับอัพเดท database"""
    try:
        # Load CSV data
        csv_file = "data/only_2_stations.csv"
        logger.info(f"Loading CSV data from {csv_file}")
        
        df = pd.read_csv(csv_file)
        logger.info(f"Loaded {len(df)} rows from CSV")
        
        # Convert Date column
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Handle NaN values
        df = df.fillna('NULL')
        
        print("=" * 80)
        print("SQL STATEMENTS TO UPDATE POSTGRESQL oil_prices_realtime TABLE")
        print("=" * 80)
        
        # Create table statement
        print("\n-- 1. CREATE TABLE (run this first if table doesn't exist)")
        print("CREATE TABLE IF NOT EXISTS oil_prices_realtime (")
        print("    id SERIAL PRIMARY KEY,")
        print("    date DATE NOT NULL,")
        print("    price_ptt DECIMAL(10,2),")
        print("    price_shell DECIMAL(10,2),")
        print("    effective_date TEXT,")
        print("    price_brent DECIMAL(10,2),")
        print("    usd_bath DECIMAL(10,4),")
        print("    price_levy DECIMAL(10,2),")
        print("    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,")
        print("    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,")
        print("    UNIQUE(date)")
        print(");")
        
        print("\n-- 2. CREATE INDEX")
        print("CREATE INDEX IF NOT EXISTS idx_oil_prices_date ON oil_prices_realtime(date);")
        
        # Clear existing data option
        print("\n-- 3. CLEAR EXISTING DATA (optional - uncomment if you want fresh start)")
        print("-- DELETE FROM oil_prices_realtime;")
        
        # Generate INSERT statements in batches
        print("\n-- 4. INSERT/UPDATE DATA")
        print("-- Using UPSERT to handle duplicates")
        
        batch_size = 100
        batch_count = 0
        
        for start_idx in range(0, len(df), batch_size):
            end_idx = min(start_idx + batch_size, len(df))
            batch_df = df.iloc[start_idx:end_idx]
            batch_count += 1
            
            print(f"\n-- Batch {batch_count}: Rows {start_idx + 1} to {end_idx}")
            print("INSERT INTO oil_prices_realtime")
            print("(date, price_ptt, price_shell, effective_date, price_brent, usd_bath, price_levy, updated_at)")
            print("VALUES")
            
            values = []
            for index, row in batch_df.iterrows():
                date_val = row['Date'].strftime('%Y-%m-%d')
                price_ptt = row['price_PTT'] if row['price_PTT'] != 'NULL' else 'NULL'
                price_shell = row['price_Shell'] if row['price_Shell'] != 'NULL' else 'NULL'
                effective_date = f"'{row['effective_date']}'" if row['effective_date'] != 'NULL' else 'NULL'
                price_brent = row['Price_Brent'] if row['Price_Brent'] != 'NULL' else 'NULL'
                usd_bath = row['USD_BATH'] if row['USD_BATH'] != 'NULL' else 'NULL'
                price_levy = row['Price_Levy'] if row['Price_Levy'] != 'NULL' else 'NULL'
                
                value_str = f"('{date_val}', {price_ptt}, {price_shell}, {effective_date}, {price_brent}, {usd_bath}, {price_levy}, CURRENT_TIMESTAMP)"
                values.append(value_str)
            
            print(",\n".join(values))
            print("ON CONFLICT (date)")
            print("DO UPDATE SET")
            print("    price_ptt = EXCLUDED.price_ptt,")
            print("    price_shell = EXCLUDED.price_shell,")
            print("    effective_date = EXCLUDED.effective_date,")
            print("    price_brent = EXCLUDED.price_brent,")
            print("    usd_bath = EXCLUDED.usd_bath,")
            print("    price_levy = EXCLUDED.price_levy,")
            print("    updated_at = CURRENT_TIMESTAMP;")
        
        print(f"\n-- 5. VERIFICATION QUERIES")
        print("SELECT COUNT(*) as total_rows FROM oil_prices_realtime;")
        print("SELECT MIN(date), MAX(date) FROM oil_prices_realtime;")
        print("SELECT * FROM oil_prices_realtime ORDER BY date DESC LIMIT 10;")
        
        print("\n" + "=" * 80)
        print("📊 SUMMARY:")
        print(f"Total rows to sync: {len(df)}")
        print(f"Date range: {df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}")
        print(f"Latest Shell price: {df.iloc[-1]['price_Shell']}")
        print(f"Latest PTT price: {df.iloc[-1]['price_PTT']}")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"Error generating SQL statements: {e}")
        return False

def show_data_summary():
    """แสดงสรุปข้อมูลใน CSV"""
    try:
        csv_file = "data/only_2_stations.csv"
        df = pd.read_csv(csv_file)
        df['Date'] = pd.to_datetime(df['Date'])
        
        print("\n" + "=" * 60)
        print("📈 CSV DATA SUMMARY")
        print("=" * 60)
        
        print(f"Total records: {len(df)}")
        print(f"Date range: {df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}")
        print(f"Columns: {', '.join(df.columns)}")
        
        print(f"\nPrice ranges:")
        print(f"PTT: {df['price_PTT'].min():.2f} - {df['price_PTT'].max():.2f}")
        print(f"Shell: {df['price_Shell'].min():.2f} - {df['price_Shell'].max():.2f}")
        
        print(f"\nLatest 5 records:")
        latest_5 = df.tail(5)[['Date', 'price_PTT', 'price_Shell', 'effective_date']]
        for _, row in latest_5.iterrows():
            print(f"  {row['Date'].strftime('%Y-%m-%d')}: PTT={row['price_PTT']}, Shell={row['price_Shell']}")
        
        # Check for data quality
        null_counts = df.isnull().sum()
        if null_counts.sum() > 0:
            print(f"\nMissing data:")
            for col, count in null_counts.items():
                if count > 0:
                    print(f"  {col}: {count} missing values")
        else:
            print(f"\n✅ No missing data found")
        
        # Verify Shell price fix
        recent_shell = df.tail(10)['price_Shell']
        if 32.65 in recent_shell.values:
            print(f"\n✅ Shell price fix verified: 32.65 found in recent data")
        if 32.15 in recent_shell.values and 32.65 in recent_shell.values:
            print(f"✅ Both old (32.15) and new (32.65) Shell prices present - shows fix progression")
        
        return True
        
    except Exception as e:
        logger.error(f"Error showing data summary: {e}")
        return False

def create_docker_commands():
    """สร้าง Docker commands สำหรับรัน PostgreSQL และ sync data"""
    print("\n" + "=" * 60)
    print("🐳 DOCKER COMMANDS TO RUN POSTGRESQL AND SYNC DATA")
    print("=" * 60)
    
    print("\n1. Start PostgreSQL with Docker:")
    print("docker run --name postgres-oil \\")
    print("  -e POSTGRES_DB=gasohol_prediction \\")
    print("  -e POSTGRES_USER=postgres \\")
    print("  -e POSTGRES_PASSWORD=postgres123 \\")
    print("  -p 5432:5432 \\")
    print("  -d postgres:13")
    
    print("\n2. Connect to PostgreSQL:")
    print("docker exec -it postgres-oil psql -U postgres -d gasohol_prediction")
    
    print("\n3. Or use docker-compose (if you have docker-compose.yml):")
    print("docker-compose up -d postgres")
    
    print("\n4. Run sync script after PostgreSQL is running:")
    print("python sync_database.py")

def main():
    """Main function"""
    print("🔧 PostgreSQL Database Sync Helper")
    print("Generates SQL and Docker commands for syncing CSV data")
    
    # Show data summary
    show_data_summary()
    
    # Ask what user wants to do
    print("\n" + "=" * 60)
    print("Choose an option:")
    print("1. Generate SQL statements to copy/paste into PostgreSQL")
    print("2. Show Docker commands to start PostgreSQL")
    print("3. Both (recommended)")
    
    try:
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice in ['1', '3']:
            print("\n🔧 Generating SQL statements...")
            generate_sql_statements()
            
        if choice in ['2', '3']:
            create_docker_commands()
            
        print("\n" + "=" * 60)
        print("✅ Helper completed!")
        print("📝 You can now copy the SQL statements or run the Docker commands")
        
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()