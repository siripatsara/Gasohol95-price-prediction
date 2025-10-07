#!/usr/bin/env python3
"""
🚨 ตรวจสอบปัญหา Next Run Time
"""

from datetime import datetime, timezone, timedelta

def check_next_run_issue():
    """ตรวจสอบว่าทำไม next run เป็น in 5 hours แทนที่จะเป็น 1 AM"""
    
    # Bangkok timezone (UTC+7)
    bangkok_tz = timezone(timedelta(hours=7))
    utc_tz = timezone.utc
    
    # เวลาปัจจุบัน
    now_bangkok = datetime.now(bangkok_tz)
    now_utc = datetime.now(utc_tz)
    
    print("🚨 NEXT RUN TIME ISSUE ANALYSIS")
    print("=" * 50)
    print(f"NOW Bangkok: {now_bangkok.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"NOW UTC:     {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Schedule: '0 18,6 * * *'
    schedule_hours_utc = [6, 18]
    
    print("📅 Schedule Analysis: '0 18,6 * * *'")
    for hour_utc in schedule_hours_utc:
        # วันนี้
        today_utc = now_utc.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
        today_bangkok = today_utc.astimezone(bangkok_tz)
        
        # พรุ่งนี้
        tomorrow_utc = today_utc + timedelta(days=1)
        tomorrow_bangkok = tomorrow_utc.astimezone(bangkok_tz)
        
        print(f"   {hour_utc:02d}:00 UTC today    = {today_bangkok.strftime('%H:%M Bangkok')} ({today_bangkok.strftime('%Y-%m-%d')})")
        print(f"   {hour_utc:02d}:00 UTC tomorrow = {tomorrow_bangkok.strftime('%H:%M Bangkok')} ({tomorrow_bangkok.strftime('%Y-%m-%d')})")
    
    print()
    
    # หาเวลา run ครั้งต่อไป
    current_hour_utc = now_utc.hour
    current_minute_utc = now_utc.minute
    
    print(f"🕐 Current time: {current_hour_utc:02d}:{current_minute_utc:02d} UTC")
    
    # คำนวณ next run
    next_runs = []
    
    for hour_utc in schedule_hours_utc:
        if current_hour_utc < hour_utc or (current_hour_utc == hour_utc and current_minute_utc < 0):
            # วันนี้
            next_run_utc = now_utc.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
            if next_run_utc > now_utc:
                next_runs.append(next_run_utc)
        
        # พรุ่งนี้
        next_run_utc = now_utc.replace(hour=hour_utc, minute=0, second=0, microsecond=0) + timedelta(days=1)
        next_runs.append(next_run_utc)
    
    # หา next run ที่เร็วที่สุด
    next_run_utc = min(next_runs)
    next_run_bangkok = next_run_utc.astimezone(bangkok_tz)
    
    time_diff = next_run_utc - now_utc
    hours_until = time_diff.total_seconds() / 3600
    
    print(f"📍 Next Run Calculation:")
    print(f"   UTC:     {next_run_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Bangkok: {next_run_bangkok.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   In {hours_until:.1f} hours")
    
    # ตรวจสอบว่าทำไมถึงเป็น 11:00:00
    problem_time_str = "2025-10-06, 11:00:00"
    print(f"\n🔍 Analyzing problematic time: {problem_time_str}")
    
    # ถ้า 11:00:00 เป็น UTC
    problem_utc = datetime(2025, 10, 6, 11, 0, 0, tzinfo=utc_tz)
    problem_bangkok = problem_utc.astimezone(bangkok_tz)
    print(f"   If 11:00 UTC  = {problem_bangkok.strftime('%H:%M Bangkok')} (NOT 01:00!)")
    
    # ถ้า 11:00:00 เป็น Bangkok 
    problem_bangkok_assumed = datetime(2025, 10, 6, 11, 0, 0, tzinfo=bangkok_tz)
    problem_utc_converted = problem_bangkok_assumed.astimezone(utc_tz)
    print(f"   If 11:00 Bangkok = {problem_utc_converted.strftime('%H:%M UTC')} (NOT in our schedule!)")
    
    print(f"\n❌ PROBLEM IDENTIFIED:")
    print(f"   Airflow is showing 11:00:00 which is WRONG")
    print(f"   Should be either:")
    print(f"   - 18:00 UTC (01:00 Bangkok) - Morning task")
    print(f"   - 06:00 UTC (13:00 Bangkok) - Afternoon task")
    
    print(f"\n💡 SOLUTION:")
    print(f"   1. Check Airflow server timezone settings")
    print(f"   2. Restart Airflow webserver and scheduler")
    print(f"   3. Verify schedule_interval format")

if __name__ == "__main__":
    check_next_run_issue()