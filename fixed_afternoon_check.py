#!/usr/bin/env python3
"""
Fixed Afternoon Check Function
ฟังก์ชันที่แก้ไขปัญหาแล้ว สำหรับ afternoon_smart_check
"""

def run_afternoon_check(**context):
    """ตรวจสอบการเปลี่ยนแปลงตอนบ่าย - แก้ไขปัญหาแล้ว"""
    from datetime import datetime  # Import ที่ต้องการ
    
    print("🌆 Afternoon Smart Check Started")
    
    try:
        # Import and use real scraper
        import sys
        sys.path.append('/opt/airflow/scraper')
        from eppo_oil_scraper import EPPOOilScraper
        
        print("🔍 Starting afternoon data comparison...")
        scraper = EPPOOilScraper()
        
        # 1. ดึงข้อมูลล่าสุดจากฐานข้อมูล (แทน get_morning_data_today ที่ไม่มี)
        latest_data = scraper.get_latest_data_from_db()
        print(f"📊 Latest data from DB: {latest_data}")
        
        # 2. Scrape ข้อมูลใหม่จากเว็บ
        scraping_data = scraper.scrape_oil_prices()
        
        if not scraping_data:
            raise Exception("Failed to scrape new data")
        
        # 3. ดึงข้อมูลเสริม
        current_usd_rate = scraper.get_usd_thb_rate()
        current_brent_price = scraper.get_brent_oil_price()
        
        print(f"💱 Current USD/THB rate: {current_usd_rate}")
        print(f"🛢️ Current Brent price: {current_brent_price}")
        
        # 4. เปรียบเทียบการเปลี่ยนแปลง
        changed_fields = []
        changes_detected = False
        
        if latest_data:
            print("🔍 Comparing afternoon data with latest DB data...")
            
            # ตรวจสอบราคา PTT
            if abs(float(latest_data.get('price_ptt', 0)) - float(scraping_data['price_ptt'])) > 0.001:
                changed_fields.append('price_ptt')
                changes_detected = True
                print(f"🔄 PTT price changed: {latest_data.get('price_ptt')} → {scraping_data['price_ptt']}")
            
            # ตรวจสอบราคา Shell
            if abs(float(latest_data.get('price_shell', 0)) - float(scraping_data['price_shell'])) > 0.001:
                changed_fields.append('price_shell')
                changes_detected = True
                print(f"🔄 Shell price changed: {latest_data.get('price_shell')} → {scraping_data['price_shell']}")
            
            # ตรวจสอบวันที่มีผล
            if latest_data.get('effective_date') != scraping_data['effective_date']:
                changed_fields.append('effective_date')
                changes_detected = True
                print(f"🔄 Effective date changed: {latest_data.get('effective_date')} → {scraping_data['effective_date']}")
            
            if not changes_detected:
                print("✅ No changes detected since last DB record")
                print("🚫 Skipping further processing tasks - data unchanged")
            else:
                print(f"🔄 Changes detected in {len(changed_fields)} field(s): {changed_fields}")
                print("⚡ Will proceed with downstream tasks - data updated")
        else:
            # ไม่มีข้อมูลเก่า ถือว่าเป็นข้อมูลใหม่
            changed_fields = ['price_ptt', 'price_shell', 'effective_date']
            changes_detected = True
            print("⚠️ No previous data found, treating as new data")
            print("⚡ Will proceed with all downstream tasks")
        
        # 5. สร้างผลลัพธ์
        scraping_result = {
            'mode': 'smart_detection',
            'date': scraping_data['date'].isoformat(),
            'price_ptt': scraping_data['price_ptt'],
            'price_shell': scraping_data['price_shell'],
            'effective_date': scraping_data['effective_date'],
            'usd_bath': current_usd_rate,
            'price_brent': current_brent_price,
            'changes_detected': changes_detected,
            'changed_fields': changed_fields,
            'total_changes': len(changed_fields),
            'execution_time': datetime.now().isoformat(),
            'database_updated': changes_detected,
            'should_continue_processing': changes_detected,  # Key field for downstream decisions
            'comparison_result': {
                'previous_data_exists': latest_data is not None,
                'compared_with': 'latest_db_data',
                'fields_checked': ['price_ptt', 'price_shell', 'effective_date'],
                'changes_summary': f"{len(changed_fields)} out of 3 fields changed" if changes_detected else "No changes detected"
            }
        }
        
        print(f"✅ Afternoon check completed!")
        print(f"📊 Should continue processing: {changes_detected}")
        print(f"🔄 Changed fields: {changed_fields}")
        
        # Share via XCom for downstream tasks to check
        context['task_instance'].xcom_push(key='scraping_result', value=scraping_result)
        context['task_instance'].xcom_push(key='should_continue_processing', value=changes_detected)
        
        return scraping_result
        
    except Exception as e:
        print(f"❌ Error in afternoon check: {e}")
        from datetime import datetime  # Add missing import
        error_result = {
            'mode': 'smart_detection',
            'changes_detected': False,
            'should_continue_processing': False,
            'execution_time': datetime.now().isoformat(),
            'database_updated': False,
            'error': str(e)
        }
        context['task_instance'].xcom_push(key='scraping_result', value=error_result)
        context['task_instance'].xcom_push(key='should_continue_processing', value=False)
        return error_result

if __name__ == "__main__":
    print("Fixed afternoon check function ready for deployment!")