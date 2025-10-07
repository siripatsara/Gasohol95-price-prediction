#!/usr/bin/env python3
"""
Timezone Debug Script
ทดสอบการแปลงเวลา UTC เป็น Bangkok timezone สำหรับ Airflow scheduling
"""

from datetime import datetime
try:
    import pendulum
    print("✅ Pendulum available")
except ImportError:
    print("❌ Pendulum not available")
    pendulum = None

def test_timezone_conversion():
    print("🕐 Testing timezone conversions for Airflow scheduling...")
    print()
    
    # Test scenarios
    test_times_utc = [
        (18, 0),  # 18:00 UTC = 01:00 Bangkok (should trigger morning)
        (6, 0),   # 06:00 UTC = 13:00 Bangkok (should trigger afternoon)
        (1, 0),   # 01:00 UTC = 08:00 Bangkok (should not trigger)
        (13, 0),  # 13:00 UTC = 20:00 Bangkok (should not trigger)
    ]
    
    for utc_hour, utc_min in test_times_utc:
        print(f"📅 Testing UTC time: {utc_hour:02d}:{utc_min:02d}")
        
        if pendulum:
            # Create UTC datetime
            utc_dt = pendulum.now('UTC').replace(hour=utc_hour, minute=utc_min, second=0, microsecond=0)
            bangkok_dt = utc_dt.in_timezone('Asia/Bangkok')
            bangkok_hour = bangkok_dt.hour
            
            print(f"   UTC: {utc_dt}")
            print(f"   Bangkok: {bangkok_dt}")
            print(f"   Bangkok hour: {bangkok_hour}")
            
            # Check what task would be triggered
            if bangkok_hour == 1:
                task = "morning_full_scrape"
            elif bangkok_hour == 13:
                task = "afternoon_smart_check"
            else:
                task = "manual_execution"
            
            print(f"   ➡️  Would trigger: {task}")
        else:
            # Fallback calculation
            bangkok_hour = (utc_hour + 7) % 24  # Bangkok is UTC+7
            print(f"   Bangkok hour (manual calc): {bangkok_hour}")
            
            if bangkok_hour == 1:
                task = "morning_full_scrape"
            elif bangkok_hour == 13:
                task = "afternoon_smart_check"
            else:
                task = "manual_execution"
            
            print(f"   ➡️  Would trigger: {task}")
        
        print()

def test_cron_schedule():
    print("📋 Current vs Corrected Cron Schedules:")
    print()
    print("❌ Current (incorrect): '0 1,13 * * *'")
    print("   - Runs at 01:00 UTC = 08:00 Bangkok")
    print("   - Runs at 13:00 UTC = 20:00 Bangkok")
    print("   - Neither matches our target hours (1 AM, 1 PM Bangkok)")
    print()
    print("✅ Corrected: '0 18,6 * * *'")
    print("   - Runs at 18:00 UTC = 01:00 Bangkok (morning)")
    print("   - Runs at 06:00 UTC = 13:00 Bangkok (afternoon)")
    print("   - Matches our target hours perfectly!")
    print()

if __name__ == "__main__":
    test_timezone_conversion()
    test_cron_schedule()