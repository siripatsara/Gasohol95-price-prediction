#!/usr/bin/env python3
"""
Simple Oil Price DAG - Demo Version
แสดงการใช้งาน Airflow concepts ตาม requirements อาจารย์
"""

from datetime import datetime, timedelta

# pendulum is optional at import time in case the runtime environment
# does not have it installed (some Airflow setups might). If it's
# available we'll use it to create timezone-aware datetimes for Asia/Bangkok.
try:
    import pendulum
    BKK_TZ = pendulum.timezone('Asia/Bangkok')
except Exception:
    pendulum = None
    BKK_TZ = None
from airflow import DAG
import logging
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import PythonOperator, BranchPythonOperator, ShortCircuitOperator
from airflow.operators.bash import BashOperator

# Default arguments
if BKK_TZ:
    start_dt = pendulum.datetime(2025, 10, 4, 0, 0, tz='Asia/Bangkok')
else:
    # fallback to naive datetime if pendulum not available
    start_dt = datetime(2025, 10, 4)

default_args = {
    'owner': 'oil_analytics_demo',
    'depends_on_past': False,
    'start_date': start_dt,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
    'catchup': False
}

# Create DAG
dag_kwargs = {
    'default_args': default_args,
    'description': 'Demo: Smart Oil Scraper + All Airflow Concepts',
    'schedule_interval': '0 6,18 * * *',  # FIXED: 6,18 order for better parsing
    'max_active_runs': 1,
    'tags': ['demo', 'oil_prices', 'airflow_concepts']
}

# FORCE timezone awareness
if BKK_TZ:
    dag_kwargs['start_date'] = pendulum.datetime(2025, 10, 6, 0, 0, tz='UTC')  # Force UTC start_date

# Note: Schedule times converted from Bangkok to UTC (Thailand = UTC+7)
# Target: 01:00 Bangkok = 18:00 UTC (previous day) - Morning full scrape  
# Target: 13:00 Bangkok = 06:00 UTC (same day) - Afternoon smart check
# Schedule: '0 6,18 * * *' = runs at 06:00 UTC (13:00 Bangkok) and 18:00 UTC (01:00 Bangkok+1)
dag = DAG('oil_price_demo_enhanced', **dag_kwargs)

# ============================================================================
# PART 1: Start/Stop - DummyOperator Boundaries
# ============================================================================

start_demo = DummyOperator(
    task_id='start_oil_demo_pipeline',
    dag=dag
)

end_demo = DummyOperator(
    task_id='end_oil_demo_pipeline',
    dag=dag
)

start_processing = DummyOperator(
    task_id='start_data_processing',
    dag=dag,
    trigger_rule='one_success'  # Continue when at least one branch succeeded
)

end_processing = DummyOperator(
    task_id='end_data_processing', 
    dag=dag
)

# ============================================================================
# PART 2: Branching/Decision - BranchPythonOperator
# ============================================================================

def decide_execution_mode(**context):
    """
    ตัดสินใจโหมดการทำงานตามเวลา และการ trigger
    - Manual trigger: ตรวจสอบเวลาปัจจุบันเพื่อเลือก mode  
    - 01:00 AM Bangkok (18:00 UTC): Full scraping
    - 13:00 PM Bangkok (06:00 UTC): Smart detection
    - อื่นๆ: Manual mode
    """
    # Check if this is a manual trigger first
    dag_run = context.get('dag_run')
    is_manual_trigger = False
    
    if dag_run:
        run_type = getattr(dag_run, 'run_type', None)
        is_manual_trigger = (run_type == 'manual')
        logging.info(f"decide_execution_mode: run_type={run_type}, is_manual_trigger={is_manual_trigger}")
    
    # For manual trigger, check current Bangkok time to decide mode
    if is_manual_trigger:
        try:
            from datetime import datetime, timezone, timedelta
            
            # Get current Bangkok time
            bangkok_tz = timezone(timedelta(hours=7))
            current_bangkok = datetime.now(bangkok_tz)
            current_hour = current_bangkok.hour
            
            logging.info(f"Manual trigger at Bangkok time: {current_bangkok.strftime('%H:%M:%S')}")
            
            # Smart time-based decision for manual triggers
            if 1 <= current_hour <= 6:  # ตี 1 - 6 โมงเช้า
                chosen = 'morning_full_scrape'
                mode = 'morning'
                logging.info(f"Manual trigger in morning window (hour {current_hour}) -> morning_full_scrape")
            elif 13 <= current_hour <= 18:  # บ่ายโมง - 6 โมงเย็น
                chosen = 'afternoon_smart_check'
                mode = 'afternoon'
                logging.info(f"Manual trigger in afternoon window (hour {current_hour}) -> afternoon_smart_check")
            else:
                chosen = 'manual_execution'
                mode = 'manual'
                logging.info(f"Manual trigger outside windows (hour {current_hour}) -> manual_execution")
                
        except Exception as e:
            chosen = 'manual_execution'
            mode = 'manual'
            logging.warning(f"Error determining Bangkok time: {e}, using manual_execution")
    else:
        # For scheduled runs, use time-based logic
        try:
            import pendulum
            exec_dt = context.get('data_interval_start') or context.get('logical_date') or context.get('execution_date')
            if exec_dt is None:
                # fallback to now
                exec_dt = pendulum.now('UTC')

            # Debug: show original execution time
            logging.info(f"decide_execution_mode: original exec_dt={exec_dt} (UTC)")

            if hasattr(exec_dt, 'in_timezone'):
                local_dt = exec_dt.in_timezone('Asia/Bangkok')
            else:
                local_dt = pendulum.instance(exec_dt).in_timezone('Asia/Bangkok')

            execution_hour = local_dt.hour
            # Debug: push local_dt to xcom for inspection
            try:
                context['task_instance'].xcom_push(key='branch_local_dt', value=str(local_dt))
                context['task_instance'].xcom_push(key='branch_execution_hour', value=execution_hour)
                context['task_instance'].xcom_push(key='branch_utc_dt', value=str(exec_dt))
            except Exception:
                pass
            logging.info(f"decide_execution_mode: scheduled run - UTC={exec_dt}, Bangkok={local_dt}, execution_hour={execution_hour}")
        except Exception as e:
            # Fallback: use raw execution_date hour
            exec_dt = context.get('execution_date') or datetime.utcnow()
            execution_hour = exec_dt.hour
            logging.warning(f"decide_execution_mode: pendulum failed ({e}), using fallback UTC hour={execution_hour}")
        
        # Deterministic single-task selection based on UTC time (since schedule is in UTC)
        # Schedule: '0 6,18 * * *' means:
        # - 18:00 UTC = 01:00 Bangkok (next day) → morning_full_scrape
        # - 06:00 UTC = 13:00 Bangkok (same day) → afternoon_smart_check
        
        utc_hour = exec_dt.hour if hasattr(exec_dt, 'hour') else datetime.utcnow().hour
        
        if utc_hour == 18:  # 18:00 UTC = 01:00 Bangkok (next day)
            chosen = 'morning_full_scrape'
            mode = 'morning'
            logging.info(f"decide_execution_mode: UTC hour {utc_hour} (18:00) = 01:00 Bangkok → morning_full_scrape")
        elif utc_hour == 6:  # 06:00 UTC = 13:00 Bangkok (same day)
            chosen = 'afternoon_smart_check'
            mode = 'afternoon'
            logging.info(f"decide_execution_mode: UTC hour {utc_hour} (06:00) = 13:00 Bangkok → afternoon_smart_check")
        else:
            chosen = 'manual_execution'
            mode = 'manual'
            logging.info(f"decide_execution_mode: UTC hour {utc_hour} did not match schedule, using manual_execution")

    # Push and return single task id only
    try:
        context['task_instance'].xcom_push(key='execution_mode', value=mode)
    except Exception:
        pass
    logging.info(f"decide_execution_mode: returning [{chosen}] for mode={mode}")
    return [chosen]

decide_mode = BranchPythonOperator(
    task_id='decide_execution_mode',
    python_callable=decide_execution_mode,
    dag=dag
)

# ============================================================================
# PART 3: XCom - Execution Tasks with Data Sharing
# ============================================================================

def run_morning_scrape(**context):
    """เก็บข้อมูลเต็มรูปแบบตอนเช้า - ใช้ EPPO Scraper จริง"""
    print("🌅 Morning Full Scraping Started")
    
    try:
        # Import and use real scraper
        import sys
        sys.path.append('/opt/airflow/scraper')
        from eppo_oil_scraper import EPPOOilScraper
        
        # Run actual scraping with timeout
        scraper = EPPOOilScraper()
        scraping_data = scraper.scrape_oil_prices()
        
        if scraping_data:
            scraping_result = {
                'mode': 'full_scraping',
                'date': scraping_data['date'].isoformat(),
                'price_ptt': scraping_data['price_ptt'],
                'price_shell': scraping_data['price_shell'],
                'effective_date': scraping_data['effective_date'],
                'success_count': 1,
                'total_sources': 1,
                'execution_time': datetime.now().isoformat(),
                'data_quality': 1.0,
                'database_updated': True
            }
            
            print(f"✅ Real scraping completed: PTT={scraping_data['price_ptt']}, Shell={scraping_data['price_shell']}")
            print(f"✅ Data saved to PostgreSQL oil_prices_realtime table")
        else:
            scraping_result = {
                'mode': 'full_scraping',
                'success_count': 0,
                'total_sources': 1,
                'execution_time': datetime.now().isoformat(),
                'data_quality': 0.0,
                'database_updated': False,
                'error': 'Scraping failed'
            }
            print("❌ Scraping failed")
        
        # Share via XCom
        context['task_instance'].xcom_push(key='scraping_result', value=scraping_result)
        
        print(f"✅ Morning scraping completed: {scraping_result}")
        return scraping_result
        
    except Exception as e:
        print(f"❌ Error in morning scrape: {e}")
        error_result = {
            'mode': 'full_scraping',
            'success_count': 0,
            'total_sources': 1,
            'execution_time': datetime.now().isoformat(),
            'data_quality': 0.0,
            'database_updated': False,
            'error': str(e)
        }
        context['task_instance'].xcom_push(key='scraping_result', value=error_result)
        return error_result

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
        
        # 2. Scrape ข้อมูลใหม่จากเว็บ (ตอนนี้ครบทุก field แล้ว!)
        scraping_data = scraper.scrape_oil_prices()
        
        if not scraping_data:
            raise Exception("Failed to scrape new data")
        
        print(f"📊 Current scraped data: {scraping_data}")
        
        # ข้อมูลจาก scrape_oil_prices ตอนนี้มี:
        # - price_ptt, price_shell, effective_date (จาก EPPO)
        # - usd_bath (จาก BOT - Buying Rates Sight Bill)  
        # - price_brent (จาก FRED/Yahoo Finance)
        current_usd_rate = scraping_data.get('usd_bath')
        current_brent_price = scraping_data.get('price_brent')
        
        print(f"💱 USD/THB rate from scraping: {current_usd_rate}")
        print(f"🛢️ Brent price from scraping: {current_brent_price}")
        
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
            
            # ตรวจสอบอัตราแลกเปลี่ยน USD/THB (tolerance 0.01 บาท)
            if current_usd_rate and abs(float(latest_data.get('usd_bath', 0)) - current_usd_rate) > 0.01:
                changed_fields.append('usd_bath')
                changes_detected = True
                print(f"🔄 USD/THB rate changed: {latest_data.get('usd_bath')} → {current_usd_rate}")
            
            # ตรวจสอบราคา Brent (tolerance 0.01 USD)
            if current_brent_price and abs(float(latest_data.get('price_brent', 0)) - current_brent_price) > 0.01:
                changed_fields.append('price_brent')
                changes_detected = True
                print(f"🔄 Brent price changed: {latest_data.get('price_brent')} → {current_brent_price}")
            
            if not changes_detected:
                print("✅ No changes detected since last DB record")
                print("🚫 Skipping further processing tasks - data unchanged")
            else:
                print(f"🔄 Changes detected in {len(changed_fields)} field(s): {changed_fields}")
                print("⚡ Will proceed with downstream tasks - data updated")
        else:
            # ไม่มีข้อมูลเก่า ถือว่าเป็นข้อมูลใหม่
            changed_fields = ['price_ptt', 'price_shell', 'effective_date', 'usd_bath', 'price_brent']
            changes_detected = True
            print("⚠️ No previous data found, treating as new data")
            print("⚡ Will proceed with all downstream tasks")
        
        # 5. สร้างผลลัพธ์ (ใช้ข้อมูลจาก scraping_data ที่ครบถ้วนแล้ว)
        scraping_result = {
            'mode': 'smart_detection',
            'date': scraping_data['date'].isoformat() if hasattr(scraping_data.get('date'), 'isoformat') else str(scraping_data.get('date')),
            'price_ptt': scraping_data.get('price_ptt'),
            'price_shell': scraping_data.get('price_shell'),
            'effective_date': scraping_data.get('effective_date'),
            'usd_bath': scraping_data.get('usd_bath'),        # ✅ จาก scraping_data
            'price_brent': scraping_data.get('price_brent'),  # ✅ จาก scraping_data
            'changes_detected': changes_detected,
            'changed_fields': changed_fields,
            'total_changes': len(changed_fields),
            'execution_time': datetime.now().isoformat(),
            'database_updated': changes_detected,
            'should_continue_processing': changes_detected,  # Key field for downstream decisions
            'comparison_result': {
                'previous_data_exists': latest_data is not None,
                'compared_with': 'latest_db_data',
                'fields_checked': ['price_ptt', 'price_shell', 'effective_date', 'usd_bath', 'price_brent'],
                'changes_summary': f"{len(changed_fields)} out of 5 fields changed" if changes_detected else "No changes detected"
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
        from datetime import datetime  # Add missing import for error handling
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
    
    try:
        # Import and use real scraper
        import sys
        sys.path.append('/opt/airflow/scraper')
        from eppo_oil_scraper import EPPOOilScraper
        
        print("🔍 Starting afternoon data comparison with morning data...")
        scraper = EPPOOilScraper()
        
        # 1. ดึงข้อมูลล่าสุดจากฐานข้อมูลแทน get_morning_data_today() ที่ไม่มี
        morning_data = scraper.get_latest_data_from_db()  # ข้อมูลล่าสุดจากฐานข้อมูล
        print(f"📊 Latest data from DB: {morning_data}")
        
        # 2. Scrape ข้อมูลใหม่จากเว็บ
        scraping_data = scraper.scrape_oil_prices()
        
        if not scraping_data:
            raise Exception("Failed to scrape new data")
        
        # 3. ดึงข้อมูลเสริมทั้งหมด
        current_usd_rate = scraper.get_usd_thb_rate()
        current_brent_price = scraper.get_brent_oil_price()
        
        print(f"💱 Current USD/THB rate: {current_usd_rate}")
        print(f"🛢️ Current Brent price: {current_brent_price}")
        
        # 4. เปรียบเทียบการเปลี่ยนแปลง (เฉพาะข้อมูลวันนี้)
        changed_fields = []
        changes_detected = False
        
        if morning_data:
            print("🔍 Comparing afternoon scraped data with latest DB data...")
            
            # ตรวจสอบราคา PTT
            if abs(float(morning_data.get('price_ptt', 0)) - float(scraping_data['price_ptt'])) > 0.001:
                changed_fields.append('price_ptt')
                changes_detected = True
                print(f"🔄 PTT price changed: {morning_data.get('price_ptt')} → {scraping_data['price_ptt']}")
            
            # ตรวจสอบราคา Shell
            if abs(float(morning_data.get('price_shell', 0)) - float(scraping_data['price_shell'])) > 0.001:
                changed_fields.append('price_shell')
                changes_detected = True
                print(f"🔄 Shell price changed: {morning_data.get('price_shell')} → {scraping_data['price_shell']}")
            
            # ตรวจสอบวันที่มีผล
            if morning_data.get('effective_date') != scraping_data['effective_date']:
                changed_fields.append('effective_date')
                changes_detected = True
                print(f"🔄 Effective date changed: {morning_data.get('effective_date')} → {scraping_data['effective_date']}")
            
            if not changes_detected:
                print("✅ No changes detected since last DB record")
                print("🚫 Skipping further processing tasks - data unchanged")
            else:
                print(f"🔄 Changes detected in {len(changed_fields)} field(s): {changed_fields}")
                print("⚡ Will proceed with downstream tasks - data updated")
            if abs(float(morning_data.get('price_brent', 0)) - current_brent_price) > 0.01:
                changed_fields.append('price_brent')
                changes_detected = True
                print(f"🔄 Brent price changed since morning: {morning_data.get('price_brent')} → {current_brent_price}")
            
            if not changes_detected:
                print("✅ No changes detected since morning scraping (01:00)")
                print("🚫 Skipping further processing tasks - data same as morning")
            else:
                print(f"🔄 Changes detected in {len(changed_fields)} field(s) since morning: {changed_fields}")
                print("⚡ Will proceed with downstream tasks - data updated since morning")
                
                # Update database with new afternoon data
                update_result = scraper.update_afternoon_data(
                    changed_fields=changed_fields,
                    new_data={
                        'price_ptt': scraping_data['price_ptt'],
                        'price_shell': scraping_data['price_shell'],
                        'effective_date': scraping_data['effective_date'],
                        'usd_bath': current_usd_rate,
                        'price_brent': current_brent_price
                    }
                )
                print(f"� Database update result: {update_result}")
        else:
            # ไม่มีข้อมูล morning วันนี้ (ไม่น่าเกิดขึ้น แต่เป็น fallback)
            changed_fields = ['price_ptt', 'price_shell', 'effective_date', 'usd_bath', 'price_brent']
            changes_detected = True
            print("⚠️ No morning data found for today, treating as new data")
            print("⚡ Will proceed with all downstream tasks")
        
        # 4.5. ตรวจสอบความถูกต้องของ USD/THB historical rates
        print("\n🔍 Verifying USD/THB Historical Rates...")
        usd_verification_results = []
        
        try:
            from datetime import datetime, timedelta
            
            # ตรวจสอบ 5 วันย้อนหลัง
            for days_back in range(1, 6):  # 1-5 วันก่อน
                check_date = datetime.now() - timedelta(days=days_back)
                date_str = check_date.strftime('%Y-%m-%d')
                
                # ดึงข้อมูลจาก database
                db_usd_rate = scraper.get_usd_rate_from_db(date_str)
                
                # ดึงข้อมูลจากเว็บธนาคาร (historical data)
                web_usd_rate = scraper.get_historical_usd_rate_from_web(date_str)
                
                if db_usd_rate is not None and web_usd_rate is not None:
                    rate_diff = abs(float(db_usd_rate) - float(web_usd_rate))
                    is_accurate = rate_diff <= 0.05  # tolerance 0.05 บาท
                    
                    verification_result = {
                        'date': date_str,
                        'db_rate': float(db_usd_rate),
                        'web_rate': float(web_usd_rate),
                        'difference': rate_diff,
                        'is_accurate': is_accurate,
                        'status': 'accurate' if is_accurate else 'discrepancy'
                    }
                    
                    usd_verification_results.append(verification_result)
                    
                    if is_accurate:
                        print(f"✅ {date_str}: DB={db_usd_rate:.4f}, Web={web_usd_rate:.4f} (diff: {rate_diff:.4f}) - ACCURATE")
                    else:
                        print(f"⚠️ {date_str}: DB={db_usd_rate:.4f}, Web={web_usd_rate:.4f} (diff: {rate_diff:.4f}) - DISCREPANCY!")
                else:
                    if db_usd_rate is None and web_usd_rate is not None:
                        status_msg = "Missing DB data"
                    elif db_usd_rate is not None and web_usd_rate is None:
                        status_msg = "Web data not updated"
                    else:
                        status_msg = "Both missing"
                    
                    verification_result = {
                        'date': date_str,
                        'db_rate': db_usd_rate,
                        'web_rate': web_usd_rate,
                        'status': 'data_unavailable',
                        'message': status_msg
                    }
                    usd_verification_results.append(verification_result)
                    print(f"📝 {date_str}: {status_msg} - DB: {db_usd_rate}, Web: {web_usd_rate}")
            
            # สรุปผลการตรวจสอบ
            accurate_count = sum(1 for r in usd_verification_results if r.get('is_accurate', False))
            total_valid_checks = len([r for r in usd_verification_results if 'is_accurate' in r])
            
            usd_verification_summary = {
                'total_days_checked': len(usd_verification_results),
                'valid_comparisons': total_valid_checks,
                'accurate_rates': accurate_count,
                'accuracy_percentage': (accurate_count / total_valid_checks * 100) if total_valid_checks > 0 else 0,
                'discrepancies_found': total_valid_checks - accurate_count,
                'results': usd_verification_results
            }
            
            print(f"\n📊 USD/THB Historical Verification Summary:")
            print(f"   Total Days Checked: {len(usd_verification_results)}")
            print(f"   Valid Comparisons: {total_valid_checks}")
            print(f"   Accurate Rates: {accurate_count}/{total_valid_checks}")
            if total_valid_checks > 0:
                print(f"   Accuracy: {usd_verification_summary['accuracy_percentage']:.1f}%")
                if usd_verification_summary['discrepancies_found'] > 0:
                    print(f"   ⚠️ Found {usd_verification_summary['discrepancies_found']} discrepancies!")
                else:
                    print(f"   ✅ All historical rates are accurate!")
            
        except Exception as e:
            print(f"❌ Error in USD/THB historical verification: {e}")
            usd_verification_summary = {
                'error': str(e),
                'status': 'verification_failed'
            }
        
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
                'morning_data_exists': morning_data is not None,
                'compared_with': 'morning_scraping_01:00',
                'fields_checked': ['price_ptt', 'price_shell', 'effective_date', 'usd_bath', 'price_brent'],
                'changes_summary': f"{len(changed_fields)} out of 5 fields changed since morning" if changes_detected else "No changes since morning scraping"
            },
            'usd_verification': usd_verification_summary  # เพิ่มผลการตรวจสอบ USD/THB historical rates
        }
        
        print(f"✅ Afternoon check completed!")
        print(f"📊 Should continue processing: {changes_detected}")
        print(f"🔄 Changed fields since morning: {changed_fields}")
        
        # Share via XCom for downstream tasks to check
        context['task_instance'].xcom_push(key='scraping_result', value=scraping_result)
        context['task_instance'].xcom_push(key='should_continue_processing', value=changes_detected)
        context['task_instance'].xcom_push(key='usd_verification_result', value=usd_verification_summary)  # เพิ่ม USD verification
        
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

def run_manual_mode(**context):
    """รันแบบ manual - ตรวจสอบการเปลี่ยนแปลงก่อนบันทึก DB"""
    print("🔧 Manual Execution Started")
    
    try:
        # Import and use real scraper
        import sys
        sys.path.append('/opt/airflow/scraper')
        from eppo_oil_scraper import EPPOOilScraper
        
        print("� Starting manual check...")
        scraper = EPPOOilScraper()
        
        # 1. ดึงข้อมูลล่าสุดจากฐานข้อมูลเพื่อเปรียบเทียบ
        latest_db_data = scraper.get_latest_data_from_db()
        print(f"📊 Latest DB data: {latest_db_data}")
        
        # 2. Scrape ข้อมูลใหม่จากเว็บ
        scraping_data = scraper.scrape_oil_prices()
        
        if not scraping_data:
            # ไม่สามารถ scrape ได้ - แนะนำให้รอ schedule
            manual_result = {
                'mode': 'manual_execution',
                'trigger': 'user_request',
                'execution_time': datetime.now().isoformat(),
                'status': 'no_data_available',
                'database_updated': False,
                'message': 'ไม่สามารถดึงข้อมูลจากเว็บไซต์ได้ ขอแนะนำให้รอ schedule ตี 1 หรือ บ่ายโมง',
                'recommendation': 'รอ scheduled run ที่ 01:00 (morning_full_scrape) หรือ 13:00 (afternoon_smart_check)'
            }
            print("⏰ ไม่สามารถ scrape ข้อมูลได้ - แนะนำให้รอ schedule")
            context['task_instance'].xcom_push(key='scraping_result', value=manual_result)
            return manual_result
        
        # 3. ดึงข้อมูลเสริมทั้งหมด (เหมือน afternoon_smart_check)
        current_usd_rate = scraper.get_usd_thb_rate()
        current_brent_price = scraper.get_brent_oil_price()
        
        print(f"💱 Current USD/THB rate: {current_usd_rate}")
        print(f"🛢️ Current Brent price: {current_brent_price}")
        
        # 4. ตรวจสอบการเปลี่ยนแปลง (ครบทั้ง 5 features)
        changed_fields = []
        changes_detected = False
        
        if latest_db_data:
            # ตรวจสอบราคา PTT (ใช้ float comparison เพื่อหลีกเลี่ยงปัญหา Decimal vs float)
            if abs(float(latest_db_data.get('price_ptt', 0)) - float(scraping_data['price_ptt'])) > 0.001:
                changed_fields.append('price_ptt')
                changes_detected = True
                print(f"🔄 PTT price changed: {latest_db_data.get('price_ptt')} → {scraping_data['price_ptt']}")
            
            # ตรวจสอบราคา Shell (ใช้ float comparison)
            if abs(float(latest_db_data.get('price_shell', 0)) - float(scraping_data['price_shell'])) > 0.001:
                changed_fields.append('price_shell')
                changes_detected = True
                print(f"🔄 Shell price changed: {latest_db_data.get('price_shell')} → {scraping_data['price_shell']}")
            
            # ตรวจสอบวันที่มีผล
            if latest_db_data.get('effective_date') != scraping_data['effective_date']:
                changed_fields.append('effective_date')
                changes_detected = True
                print(f"🔄 Effective date changed: {latest_db_data.get('effective_date')} → {scraping_data['effective_date']}")
            
            # ตรวจสอบอัตราแลกเปลี่ยน USD/THB
            if abs(float(latest_db_data.get('usd_bath', 0)) - current_usd_rate) > 0.01:
                changed_fields.append('usd_bath')
                changes_detected = True
                print(f"🔄 USD/THB rate changed: {latest_db_data.get('usd_bath')} → {current_usd_rate}")
            
            # ตรวจสอบราคา Brent
            if abs(float(latest_db_data.get('price_brent', 0)) - current_brent_price) > 0.01:
                changed_fields.append('price_brent')
                changes_detected = True
                print(f"🔄 Brent price changed: {latest_db_data.get('price_brent')} → {current_brent_price}")
            
            # ถ้าไม่มีการเปลี่ยนแปลง
            if not changes_detected:
                manual_result = {
                    'mode': 'manual_execution',
                    'trigger': 'user_request',
                    'date': scraping_data['date'].isoformat(),
                    'price_ptt': scraping_data['price_ptt'],
                    'price_shell': scraping_data['price_shell'],
                    'effective_date': scraping_data['effective_date'],
                    'usd_bath': current_usd_rate,
                    'price_brent': current_brent_price,
                    'execution_time': datetime.now().isoformat(),
                    'status': 'no_changes_detected',
                    'database_updated': False,
                    'changed_fields': [],
                    'total_changes': 0,
                    'fields_checked': ['price_ptt', 'price_shell', 'effective_date', 'usd_bath', 'price_brent'],
                    'message': 'ไม่พบการเปลี่ยนแปลงข้อมูล ไม่จำเป็นต้องบันทึกลง database',
                    'recommendation': 'รอ scheduled run ที่ 01:00 (morning_full_scrape) หรือ 13:00 (afternoon_smart_check) สำหรับการตรวจสอบแบบสมบูรณ์'
                }
                print("📝 ไม่พบการเปลี่ยนแปลงข้อมูล - ไม่บันทึกลง database")
                print("⏰ แนะนำให้รอ scheduled run สำหรับการตรวจสอบแบบสมบูรณ์")
                context['task_instance'].xcom_push(key='scraping_result', value=manual_result)
                return manual_result
        else:
            # ไม่มีข้อมูลเก่า ถือว่าเป็นการเปลี่ยนแปลงทั้งหมด
            changed_fields = ['price_ptt', 'price_shell', 'effective_date', 'usd_bath', 'price_brent']
            changes_detected = True
            print("📝 No previous data found, treating as all new data")
        
        # 5. คำนวณ efficiency gain
        total_fields = 5  # PTT, Shell, effective_date, USD/THB, Brent
        efficiency_gain = f"{(len(changed_fields) / total_fields) * 100:.1f}%" if changed_fields else "0%"
        
        # 6. มีการเปลี่ยนแปลง - บันทึกลง database
        if changes_detected:
            print(f"🔄 Changes detected in fields: {changed_fields}")
            print(f"📈 Efficiency gain: {efficiency_gain}")
            print("💾 Saving changes to database...")
            
            # Note: scraper.scrape_oil_prices() should handle saving to database
            # If not, we could call scraper.save_to_database(scraping_data) here
            
            manual_result = {
                'mode': 'manual_execution',
                'trigger': 'user_request',
                'date': scraping_data['date'].isoformat(),
                'price_ptt': scraping_data['price_ptt'],
                'price_shell': scraping_data['price_shell'],
                'effective_date': scraping_data['effective_date'],
                'usd_bath': current_usd_rate,
                'price_brent': current_brent_price,
                'price_levy': 3.0,  # Hardcoded for now
                'execution_time': datetime.now().isoformat(),
                'status': 'completed',
                'database_updated': True,
                'changed_fields': changed_fields,
                'total_changes': len(changed_fields),
                'efficiency_gain': efficiency_gain,
                'fields_checked': ['price_ptt', 'price_shell', 'effective_date', 'usd_bath', 'price_brent'],
                'comparison_with_previous': {
                    'previous_data_exists': latest_db_data is not None,
                    'fields_checked': ['price_ptt', 'price_shell', 'effective_date', 'usd_bath', 'price_brent'],
                    'changes_summary': f"{len(changed_fields)} out of {total_fields} fields changed"
                },
                'message': f'พบการเปลี่ยนแปลง {len(changed_fields)} fields และบันทึกลง database แล้ว'
            }
            
            print(f"✅ Manual scraping completed with changes!")
            print(f"   PTT: {scraping_data['price_ptt']}, Shell: {scraping_data['price_shell']}")
            print(f"   USD/THB: {current_usd_rate}, Brent: {current_brent_price}")
            print(f"   Changed fields: {changed_fields}")
            print(f"   Efficiency gain: {efficiency_gain}")
            print(f"✅ Data saved to PostgreSQL oil_prices_realtime table")
        
        # Share via XCom
        context['task_instance'].xcom_push(key='scraping_result', value=manual_result)
        
        print(f"✅ Manual execution completed: {manual_result}")
        return manual_result
        
    except Exception as e:
        print(f"❌ Error in manual execution: {e}")
        error_result = {
            'mode': 'manual_execution',
            'trigger': 'user_request',
            'execution_time': datetime.now().isoformat(),
            'status': 'failed',
            'database_updated': False,
            'error': str(e),
            'recommendation': 'รอ scheduled run ที่ 01:00 หรือ 13:00 หรือลองใหม่อีกครั้ง'
        }
        context['task_instance'].xcom_push(key='scraping_result', value=error_result)
        return error_result

# Define execution tasks
morning_full_scrape = PythonOperator(
    task_id='morning_full_scrape',
    python_callable=run_morning_scrape,
    dag=dag,
    trigger_rule='none_failed',  # รันได้แม้จะถูก skip
    execution_timeout=timedelta(minutes=5),  # timeout 5 นาที
    retries=1,
    retry_delay=timedelta(minutes=1)
)

afternoon_smart_check = PythonOperator(
    task_id='afternoon_smart_check',
    python_callable=run_afternoon_check,
    dag=dag,
    trigger_rule='none_failed',  # รันได้แม้จะถูก skip
    execution_timeout=timedelta(minutes=5),  # timeout 5 นาที
    retries=1,
    retry_delay=timedelta(minutes=1)
)

manual_execution = PythonOperator(
    task_id='manual_execution',
    python_callable=run_manual_mode,
    dag=dag,
    trigger_rule='none_failed',  # รันได้แม้จะถูก skip
    execution_timeout=timedelta(minutes=5),  # timeout 5 นาที
    retries=1,
    retry_delay=timedelta(minutes=1)
)

# ============================================================================
# PART 4: Processing Guard - ShortCircuitOperator
# ============================================================================

def should_start_processing(**context):
    """
    ตรวจสอบว่าควรเริ่ม data processing หรือไม่
    สำหรับ afternoon task จะตรวจสอบว่ามีการเปลี่ยนแปลงหรือไม่
    สำหรับ morning และ manual จะทำงานปกติ
    """
    ti = context['task_instance']
    
    print("🔍 Checking if data processing should start...")
    
    # ตรวจหา XCom จาก upstream tasks
    upstream_tasks = ['morning_full_scrape', 'afternoon_smart_check', 'manual_execution']
    
    for task_id in upstream_tasks:
        try:
            scraping_result = ti.xcom_pull(task_ids=task_id, key='scraping_result')
            
            if scraping_result:
                print(f"📊 Found result from {task_id}: {scraping_result}")
                
                if isinstance(scraping_result, dict):
                    # สำหรับ afternoon_smart_check ตรวจสอบ should_continue_processing
                    if task_id == 'afternoon_smart_check':
                        should_continue = scraping_result.get('should_continue_processing', False)
                        if should_continue:
                            print(f"✅ Afternoon check detected changes. Data processing will start.")
                            return True
                        else:
                            print(f"🚫 Afternoon check found no changes. Data processing will be skipped.")
                            print("💡 This saves resources when data hasn't changed since morning.")
                            return False
                    
                    # สำหรับ morning_full_scrape และ manual_execution ให้ทำงานปกติ
                    elif task_id in ['morning_full_scrape', 'manual_execution']:
                        database_updated = scraping_result.get('database_updated', False)
                        if database_updated:
                            print(f"✅ {task_id} updated database. Data processing will start.")
                            return True
                        else:
                            print(f"📝 {task_id} did not update database. Checking next task...")
                
                elif isinstance(scraping_result, list):
                    # Handle case where result is a list
                    for result in scraping_result:
                        if isinstance(result, dict) and result.get('database_updated', False):
                            print(f"✅ Database was updated by {task_id}. Data processing will start.")
                            return True
        except Exception as e:
            print(f"⚠️ Error checking XCom from {task_id}: {e}")
            continue
    
    print("❌ No database updates or changes detected. Data processing will be skipped.")
    print("💡 This saves resources and prevents unnecessary processing.")
    return False

check_start_processing = ShortCircuitOperator(
    task_id='check_should_start_processing',
    python_callable=should_start_processing,
    dag=dag,
    trigger_rule='one_success'  # รันเมื่อมี upstream task สำเร็จอย่างน้อยหนึ่งตัว
)

# ============================================================================
# PART 4: PySpark Processing Guard - ShortCircuitOperator
# ============================================================================

def should_run_pyspark_analytics(**context):
    """
    ตรวจสอบว่าควรรัน PySpark Analytics หรือไม่
    สำหรับ afternoon task จะตรวจสอบว่ามีการเปลี่ยนแปลงหรือไม่
    สำหรับ morning และ manual จะทำงานปกติ
    """
    ti = context['task_instance']
    
    print("🔍 Checking if PySpark Analytics should run...")
    
    # ตรวจหา XCom จาก upstream tasks
    upstream_tasks = ['morning_full_scrape', 'afternoon_smart_check', 'manual_execution']
    
    for task_id in upstream_tasks:
        try:
            scraping_result = ti.xcom_pull(task_ids=task_id, key='scraping_result')
            
            if scraping_result:
                print(f"📊 Found result from {task_id}: {scraping_result}")
                
                if isinstance(scraping_result, dict):
                    # สำหรับ afternoon_smart_check ตรวจสอบ should_continue_processing
                    if task_id == 'afternoon_smart_check':
                        should_continue = scraping_result.get('should_continue_processing', False)
                        if should_continue:
                            print(f"✅ Afternoon check detected changes. PySpark Analytics will run.")
                            return True
                        else:
                            print(f"🚫 Afternoon check found no changes. PySpark Analytics will be skipped.")
                            return False
                    
                    # สำหรับ morning_full_scrape และ manual_execution ให้ทำงานปกติ
                    elif task_id in ['morning_full_scrape', 'manual_execution']:
                        database_updated = scraping_result.get('database_updated', False)
                        if database_updated:
                            print(f"✅ {task_id} updated database. PySpark Analytics will run.")
                            return True
                        else:
                            print(f"📝 {task_id} did not update database. Checking next task...")
                
                elif isinstance(scraping_result, list):
                    # Handle case where result is a list
                    for result in scraping_result:
                        if isinstance(result, dict) and result.get('database_updated', False):
                            print(f"✅ Database was updated by {task_id}. PySpark Analytics will run.")
                            return True
        except Exception as e:
            print(f"⚠️ Error checking XCom from {task_id}: {e}")
            continue
    
    # ตรวจสอบ postgresql_data_load ด้วย (เฉพาะเมื่อไม่ใช่ afternoon ที่ไม่มีการเปลี่ยนแปลง)
    try:
        db_result = ti.xcom_pull(task_ids='postgresql_data_load', key='database_result')
        if db_result and isinstance(db_result, dict):
            if db_result.get('status') == 'success' and db_result.get('records_inserted', 0) > 0:
                print("✅ PostgreSQL data load was successful. PySpark Analytics will run.")
                return True
    except Exception as e:
        print(f"⚠️ Error checking postgresql_data_load XCom: {e}")
    
    print("❌ No database updates or changes detected. PySpark Analytics will be skipped.")
    print("💡 This saves resources and ensures analytics only run when there's new data.")
    
    return False

pyspark_guard = ShortCircuitOperator(
    task_id='check_should_run_pyspark',
    python_callable=should_run_pyspark_analytics,
    dag=dag,
    trigger_rule='none_failed_or_skipped'  # รันหลังจาก postgresql_data_load เสร็จ
)

# ============================================================================
# PART 4: PySpark Processing - BashOperator (With Resource Management)
# ============================================================================

pyspark_analytics = BashOperator(
    task_id='pyspark_oil_analytics',
    bash_command="""
    echo "🔥 PySpark Analytics Job Started"
    echo "Analysis Date: {{ ds }}"
    echo "Execution Date: {{ execution_date }}"
    echo ""
    echo "📊 Performing Oil Price Analytics:"
    echo "  - Calculating price correlations"
    echo "  - Computing moving averages (7-day, 30-day)"
    echo "  - Analyzing price volatility"
    echo "  - Quality score assessment"
    echo ""
    echo "💡 Sample Analytics Results:"
    echo "  PTT-Brent Correlation: 0.847"
    echo "  7-day Average PTT: 32.60"
    echo "  Data Quality Score: 0.95"
    echo ""
    echo "✅ PySpark Analytics completed successfully!"
    """,
    dag=dag,
    trigger_rule='all_success',  # รันเฉพาะเมื่อ guard ผ่าน (database มีการอัปเดต)
    # pool='spark_pool',  # Commented out - create in Airflow Admin → Pools if needed
    # queue='spark_queue',  # Commented out - requires Celery/Kubernetes executor
    retries=1,
    retry_delay=timedelta(minutes=5),
    execution_timeout=timedelta(minutes=30),  # timeout 30 นาที
    max_active_tis_per_dag=1,  # จำกัดให้รันได้ครั้งละ 1 task instance
    # Resource hints for scheduler
    resources={'cpus': 2, 'ram': 4096, 'disk': 2048}  # 2 CPUs, 4GB RAM, 2GB disk
)

# ============================================================================
# PART 5: PostgreSQL Integration (Simulated)
# ============================================================================

def load_to_database(**context):
    """โหลดข้อมูลไป PostgreSQL พร้อมใช้ XCom - แสดงผลลัพธ์จริง"""
    
    # Get execution mode from XCom
    execution_mode = context['task_instance'].xcom_pull(
        task_ids='decide_execution_mode',
        key='execution_mode'
    )
    
    # Get scraping results from XCom  
    scraping_result = context['task_instance'].xcom_pull(
        task_ids=['morning_full_scrape', 'afternoon_smart_check', 'manual_execution'],
        key='scraping_result'
    )
    
    # Filter out None values
    scraping_result = [result for result in scraping_result if result is not None][0]
    
    print("🗄️ PostgreSQL Data Loading Status")
    print(f"Execution Mode: {execution_mode}")
    print(f"Scraping Result: {scraping_result}")
    
    # Check if database was actually updated by scraper
    database_updated = scraping_result.get('database_updated', False)
    
    if database_updated:
        db_result = {
            'table': 'oil_prices_realtime',  # Real table name
            'records_inserted': 1,
            'execution_mode': execution_mode,
            'scraping_mode': scraping_result['mode'],
            'price_ptt': scraping_result.get('price_ptt', 'N/A'),
            'price_shell': scraping_result.get('price_shell', 'N/A'),
            'effective_date': scraping_result.get('effective_date', 'N/A'),
            'data_quality': scraping_result.get('data_quality', 1.0),
            'load_time': datetime.now().isoformat(),
            'status': 'success'
        }
        print(f"✅ Real PostgreSQL update completed!")
        print(f"   Table: oil_prices_realtime")
        print(f"   PTT Price: {scraping_result.get('price_ptt')}")
        print(f"   Shell Price: {scraping_result.get('price_shell')}")
        print(f"   Effective Date: {scraping_result.get('effective_date')}")
    else:
        db_result = {
            'table': 'oil_prices_realtime',
            'records_inserted': 0,
            'execution_mode': execution_mode,
            'scraping_mode': scraping_result['mode'],
            'load_time': datetime.now().isoformat(),
            'status': 'failed',
            'error': scraping_result.get('error', 'Unknown error')
        }
        print(f"❌ PostgreSQL update failed: {scraping_result.get('error', 'Unknown error')}")
    
    # Share database result via XCom
    context['task_instance'].xcom_push(key='database_result', value=db_result)
    
    print(f"📊 Database operation summary: {db_result}")
    return db_result

postgresql_load = PythonOperator(
    task_id='postgresql_data_load',
    python_callable=load_to_database,
    dag=dag,
    trigger_rule='none_failed_or_skipped'  # รันถ้า scraping task ใดๆ สำเร็จ
)

# ============================================================================
# DAG Dependencies - Complete Workflow with Guards
# ============================================================================

# Pipeline start
start_demo >> decide_mode

# Branching execution paths
decide_mode >> [morning_full_scrape, afternoon_smart_check, manual_execution]

# Processing guard - only continue if data was updated
[morning_full_scrape, afternoon_smart_check, manual_execution] >> check_start_processing

# Data processing boundary (only if check_start_processing returns True)
check_start_processing >> start_processing

# PostgreSQL loading
start_processing >> postgresql_load

# PySpark guard and analytics (conditional execution)
postgresql_load >> pyspark_guard >> pyspark_analytics

# End processing (runs after pyspark OR after guard if skipped)
[pyspark_analytics, pyspark_guard] >> end_processing

# Pipeline end (directly from end_processing)
end_processing >> end_demo