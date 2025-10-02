#!/usr/bin/env python3
"""
EPPO Oil Fund Levy Scraper
Scrapes Oil Fund Levy data for Gasohol 95 (E10) from EPPO Excel file
"""

import os
import sys
import pandas as pd
import requests
import logging
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import shutil

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/eppo_levy_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EPPOLevyScraper:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"
        self.csv_file = self.data_dir / "only_2_stations.csv"
        
        # Excel file URL and paths - เก็บแค่ 2 ไฟล์: current และ previous
        self.excel_url = "https://www.eppo.go.th/epposite/images/Energy-Statistics/energyinformation/Energy_Statistics/Petroleum_Prices/P06.xls"
        self.current_excel = self.data_dir / "P06_current.xls"
        self.previous_excel = self.data_dir / "P06_previous.xls"
        
    def download_excel_file(self):
        """Download the Excel file from EPPO website"""
        try:
            logger.info("Downloading Excel file from EPPO...")
            
            # หากมีไฟล์ current อยู่แล้ว ให้ย้ายเป็น previous ก่อน
            if self.current_excel.exists():
                if self.previous_excel.exists():
                    self.previous_excel.unlink()  # ลบไฟล์เก่า
                shutil.move(str(self.current_excel), str(self.previous_excel))
                logger.info("Moved current file to previous")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(self.excel_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            with open(self.current_excel, 'wb') as f:
                f.write(response.content)
                
            logger.info(f"Excel file downloaded successfully: {self.current_excel}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download Excel file: {e}")
            return False
    
    def get_file_hash(self, file_path):
        """Calculate MD5 hash of a file"""
        if not file_path.exists():
            return None
            
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def compare_with_previous_file(self):
        """Compare current file with previous day's file"""
        if not self.previous_excel.exists():
            logger.info("No previous file found for comparison")
            return False, "no_previous_file"
        
        current_hash = self.get_file_hash(self.current_excel)
        previous_hash = self.get_file_hash(self.previous_excel)
        
        if current_hash == previous_hash:
            logger.info("Excel file unchanged from previous day")
            return True, "unchanged"
        else:
            logger.info("Excel file has been updated")
            return False, "updated"
    
    def parse_excel_data(self, excel_path):
        """Parse Excel file and extract Gasohol 95 (E10) levy data"""
        try:
            logger.info(f"Parsing Excel file: {excel_path}")
            
            # Try to read Excel file with different engines
            try:
                df = pd.read_excel(excel_path, engine='xlrd', header=None)
            except:
                df = pd.read_excel(excel_path, engine='openpyxl', header=None)
            
            logger.info(f"Excel file loaded with shape: {df.shape}")
            
            # Find the header rows
            header_main_row = None
            header_sub_row = None
            
            # Look for main header row (should contain DATE, GASOHOL 95)
            for idx in range(min(15, len(df))):
                row_values = [str(cell).upper() if pd.notna(cell) else "" for cell in df.iloc[idx].values]
                if 'DATE' in row_values and any('GASOHOL' in val for val in row_values):
                    header_main_row = idx
                    break
            
            # Look for sub-header row (should contain E10, E20)
            if header_main_row is not None:
                for idx in range(header_main_row + 1, min(header_main_row + 5, len(df))):
                    row_values = [str(cell).upper() if pd.notna(cell) else "" for cell in df.iloc[idx].values]
                    if any('E10' in val for val in row_values):
                        header_sub_row = idx
                        break
            
            if header_main_row is None:
                logger.error("Could not find main header row")
                return None
            
            logger.info(f"Found main header at row {header_main_row}")
            if header_sub_row:
                logger.info(f"Found sub header at row {header_sub_row}")
            
            # Extract column information
            main_headers = df.iloc[header_main_row].values
            sub_headers = df.iloc[header_sub_row].values if header_sub_row else [None] * len(main_headers)
            
            # Find the DATE column and GASOHOL 95 (E10) column
            date_col_idx = None
            gasohol95_e10_col_idx = None
            
            for i, (main_header, sub_header) in enumerate(zip(main_headers, sub_headers)):
                main_str = str(main_header).upper().strip() if pd.notna(main_header) else ""
                sub_str = str(sub_header).upper().strip() if pd.notna(sub_header) else ""
                
                if 'DATE' in main_str:
                    date_col_idx = i
                    logger.info(f"Found DATE column at index {i}")
                
                # Look for GASOHOL 95 in main header and (E10) in sub header
                if 'GASOHOL' in main_str and '95' in main_str and '(E10)' in sub_str:
                    gasohol95_e10_col_idx = i
                    logger.info(f"Found GASOHOL 95 (E10) column at index {i}")
                    logger.info(f"Main header: '{main_header}', Sub header: '{sub_header}'")
            
            if date_col_idx is None:
                logger.error("Could not find DATE column")
                return None
            
            if gasohol95_e10_col_idx is None:
                logger.error("Could not find GASOHOL 95 (E10) column")
                return None
            
            # Extract data starting from after the header rows
            data_start_row = (header_sub_row if header_sub_row else header_main_row) + 1
            
            levy_data = []
            current_year = datetime.now().year  # ใช้ปีปัจจุบันจากระบบ
            
            for idx in range(data_start_row, len(df)):
                try:
                    date_val = df.iloc[idx, date_col_idx]
                    levy_val = df.iloc[idx, gasohol95_e10_col_idx]
                    
                    # Check if this row contains year information
                    if isinstance(date_val, (str, int)) and str(date_val).strip().isdigit():
                        year_val = int(str(date_val).strip())
                        if year_val >= 2000 and year_val <= (datetime.now().year + 5):  # ช่วงปีที่สมเหตุสมผล
                            current_year = year_val
                            logger.info(f"Found year in Excel file: {current_year}")
                            continue
                    
                    # Skip if date or levy is NaN/None
                    if pd.isna(date_val) or pd.isna(levy_val):
                        continue
                    
                    # Skip rows with 'AVG' or other non-date values
                    if isinstance(date_val, str) and date_val.strip().upper() in ['AVG', 'AVERAGE']:
                        continue
                    
                    # Parse date - จัดการรูปแบบวันที่ตาม Excel (AUG-4, SEP-1, etc.)
                    if isinstance(date_val, str):
                        try:
                            date_str = date_val.strip().upper()
                            if '-' in date_str:
                                # Format: AUG-4, SEP-1, OCT-6, etc.
                                month_day = date_str.split('-')
                                if len(month_day) == 2:
                                    month_str = month_day[0]
                                    day_str = month_day[1]
                                    
                                    # Convert month abbreviation to number
                                    month_map = {
                                        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
                                        'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
                                    }
                                    
                                    if month_str in month_map:
                                        month = month_map[month_str]
                                        day = int(day_str)
                                        # ใช้ปีที่พบจากไฟล์
                                        date_parsed = datetime(current_year, month, day)
                                    else:
                                        continue
                                else:
                                    continue
                            elif date_str in ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 
                                            'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']:
                                # ถ้าเป็นชื่อเดือนอย่างเดียว ข้าม
                                continue
                            else:
                                # ลองแปลงรูปแบบอื่นๆ
                                date_parsed = pd.to_datetime(date_val)
                        except:
                            continue
                    else:
                        try:
                            date_parsed = pd.to_datetime(date_val)
                        except:
                            continue
                    
                    # Parse levy value - จัดการค่าที่อาจจะเป็นลบ (ในวงเล็บ)
                    if isinstance(levy_val, str):
                        levy_str = levy_val.strip()
                        # ถ้าเป็นค่าในวงเล็บ เช่น (4.4443) แปลว่าเป็นค่าลบ
                        if levy_str.startswith('(') and levy_str.endswith(')'):
                            levy_val = -float(levy_str[1:-1])
                        elif levy_str.replace('.', '').replace('-', '').isdigit():
                            levy_val = float(levy_str)
                        else:
                            continue
                    else:
                        levy_val = float(levy_val)
                    
                    levy_data.append({
                        'date': date_parsed.date(),
                        'price_levy': levy_val
                    })
                    
                except Exception as e:
                    logger.warning(f"Could not parse row {idx}: {e}")
                    continue
            
            logger.info(f"Extracted {len(levy_data)} levy records")
            if levy_data:
                logger.info(f"First record: {levy_data[0]}")
                logger.info(f"Latest record: {levy_data[-1]}")
            
            return levy_data
            
        except Exception as e:
            logger.error(f"Failed to parse Excel file: {e}")
            return None
    
    def update_csv_with_levy_data(self, levy_data, historical_changes=None):
        """Update CSV file with levy data and handle historical changes"""
        try:
            # Read existing CSV
            df = pd.read_csv(self.csv_file)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            
            # Add Price_Levy column if it doesn't exist
            if 'Price_Levy' not in df.columns:
                df['Price_Levy'] = None
            
            # Create a dictionary for quick lookup
            levy_dict = {item['date']: item['price_levy'] for item in levy_data}
            
            # Get the latest levy date and value
            latest_levy_date = max(levy_dict.keys())
            latest_levy_value = levy_dict[latest_levy_date]
            
            logger.info(f"Latest levy data: {latest_levy_date} -> {latest_levy_value}")
            
            # Handle historical changes first
            if historical_changes:
                logger.info(f"Applying {len(historical_changes)} historical changes to CSV")
                for change in historical_changes:
                    change_date = change['date']
                    new_value = change['new_value']
                    old_value = change['old_value']
                    
                    # Update the specific date
                    mask = df['Date'] == change_date
                    if mask.any():
                        df.loc[mask, 'Price_Levy'] = new_value
                        logger.info(f"Updated {change_date}: {old_value} -> {new_value}")
                    
                    # Also update any dates after this change that might have been forward-filled
                    # with the old value, but only if they don't have exact data
                    dates_after = df['Date'] > change_date
                    dates_not_in_levy = ~df['Date'].isin(levy_dict.keys())
                    dates_with_old_value = df['Price_Levy'] == old_value
                    
                    update_mask = dates_after & dates_not_in_levy & dates_with_old_value
                    if update_mask.any():
                        affected_count = update_mask.sum()
                        logger.info(f"Updating {affected_count} forward-filled dates after {change_date}")
            
            # Update CSV data with current levy information
            updated_rows = 0
            for idx, row in df.iterrows():
                date = row['Date']
                
                if date in levy_dict:
                    # Direct match - use exact value
                    df.at[idx, 'Price_Levy'] = levy_dict[date]
                    updated_rows += 1
                elif date > latest_levy_date:
                    # Forward fill for dates after latest levy data
                    df.at[idx, 'Price_Levy'] = latest_levy_value
                    updated_rows += 1
            
            # Save updated CSV
            df.to_csv(self.csv_file, index=False)
            logger.info(f"Updated {updated_rows} rows with levy data")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update CSV with levy data: {e}")
            return False
    
    def check_historical_changes(self, current_data, previous_excel_path):
        """Check for historical changes between current and previous Excel data"""
        if not previous_excel_path.exists():
            logger.info("No previous Excel file for historical comparison")
            return []
        
        try:
            previous_data = self.parse_excel_data(previous_excel_path)
            if not previous_data:
                return []
            
            # Create dictionaries for comparison
            current_dict = {item['date']: item['price_levy'] for item in current_data}
            previous_dict = {item['date']: item['price_levy'] for item in previous_data}
            
            # Find differences
            changes = []
            for date, current_value in current_dict.items():
                if date in previous_dict:
                    previous_value = previous_dict[date]
                    if abs(current_value - previous_value) > 0.001:  # Small tolerance for float comparison
                        changes.append({
                            'date': date,
                            'old_value': previous_value,
                            'new_value': current_value
                        })
            
            if changes:
                logger.info(f"Found {len(changes)} historical changes")
                for change in changes:
                    logger.info(f"  {change['date']}: {change['old_value']} -> {change['new_value']}")
            
            return changes
            
        except Exception as e:
            logger.error(f"Failed to check historical changes: {e}")
            return []
    
    def run(self):
        """Main execution method"""
        try:
            logger.info("=== Starting EPPO Levy Scraping ===")
            
            # Download current Excel file
            if not self.download_excel_file():
                logger.error("Failed to download Excel file")
                return False
            
            # Compare with previous file
            is_same, comparison_result = self.compare_with_previous_file()
            
            if is_same and comparison_result == "unchanged":
                logger.info("File unchanged - using forward-fill logic")
                # Still need to update CSV for new dates using previous file
                levy_data = self.parse_excel_data(self.previous_excel if self.previous_excel.exists() else self.current_excel)
                if levy_data:
                    self.update_csv_with_levy_data(levy_data)
                return True
            
            # Parse current Excel data
            current_data = self.parse_excel_data(self.current_excel)
            if not current_data:
                logger.error("Failed to parse Excel data")
                return False
            
            # Check for historical changes if file was updated
            historical_changes = []
            if comparison_result == "updated":
                historical_changes = self.check_historical_changes(current_data, self.previous_excel)
                if historical_changes:
                    logger.info("Historical changes detected - will update CSV accordingly")
            
            # Update CSV with levy data and historical changes
            if not self.update_csv_with_levy_data(current_data, historical_changes):
                logger.error("Failed to update CSV with levy data")
                return False
            
            # ลบไฟล์เก่าหลังจากใช้เปรียบเทียบเสร็จแล้ว
            if self.previous_excel.exists():
                self.previous_excel.unlink()
                logger.info("Removed previous Excel file after processing")
            
            logger.info("=== EPPO Levy Scraping completed successfully ===")
            return True
            
        except Exception as e:
            logger.error(f"Levy scraping failed: {e}")
            return False

def main():
    """Main function"""
    scraper = EPPOLevyScraper()
    success = scraper.run()
    
    if success:
        print("✅ EPPO Levy scraping completed successfully!")
    else:
        print("❌ EPPO Levy scraping failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()