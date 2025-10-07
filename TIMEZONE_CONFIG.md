# Oil Price Scraper - Timezone Configuration Summary
# สรุปการตั้งค่าเวลาสำหรับระบบ Scraping

## 📅 วันที่อัปเดต: 3 ตุลาคม 2025

## ⏰ กำหนดการรัน (Asia/Bangkok Timezone)

### เวลารัน Scraper:
- **00:05 น.** (เที่ยงคืน) - Full scraping
- **12:05 น.** (เที่ยงวัน) - Smart update

### Cron Expression:
```
5 0,12 * * *
```
- `5` = นาทีที่ 5
- `0,12` = ชั่วโมง 0 (เที่ยงคืน) และ 12 (เที่ยงวัน)
- `* * *` = ทุกวัน ทุกเดือน ทุกปี

## 🔧 ไฟล์ที่แก้ไขแล้ว

### 1. Docker Compose Configuration
**ไฟล์:** `docker-compose-airflow.yml`

เพิ่ม Timezone Settings:
```yaml
environment:
  AIRFLOW__CORE__DEFAULT_TIMEZONE: 'Asia/Bangkok'
  TZ: 'Asia/Bangkok'
```

ทั้งใน:
- `airflow-webserver` service
- `airflow-scheduler` service

### 2. Airflow DAG Files

#### `oil_price_scraper_dag.py` (DAG หลัก)
- Schedule: `'5 0,12 * * *'`
- Description: รันเวลา 00:05 และ 12:05 น.
- Tags: `['oil-price', 'scraping', 'smart-update']`

#### `oil_price_scraper_morning.py`
- Schedule: `'5 12 * * *'`
- Description: รันเวลา 12:05 น. (เที่ยงวัน)
- Tags: `['oil-price', 'scraping', 'morning']`

#### `oil_price_scraper_evening.py`
- Schedule: `'5 0 * * *'`
- Description: รันเวลา 00:05 น. (เที่ยงคืน)
- Tags: `['oil-price', 'scraping', 'evening']`

#### `oil_price_analytics_dag.py`
- Schedule: `'5 0,12 * * *'`
- Description: Analytics DAG รันเวลา 00:05 และ 12:05 น.

#### `oil_price_demo_dag.py`
- Schedule: `'5 18,6 * * *'` (UTC time for demo)
- Description: Demo DAG

### 3. Smart Oil Scraper Logic
**ไฟล์:** `scraper/smart_oil_scraper.py`

ฟังก์ชัน `get_current_time_context()`:
```python
def get_current_time_context(self):
    """ตรวจสอบว่าตอนนี้เป็นเวลา 12:05 AM หรือ 12:05 PM"""
    current_hour = datetime.now().hour
    
    if current_hour == 0:
        return 'midnight', '12:05 AM - Full scraping'
    elif current_hour == 12:
        return 'noon', '12:05 PM - Smart update'
    else:
        return 'other', f'{current_hour}:05 - Manual execution'
```

## 🚀 วิธีใช้งาน

### 1. รีสตาร์ท Airflow (Windows PowerShell)
```powershell
cd E:\year4_1\T.Boat\programs\perfect
.\restart_airflow.ps1
```

หรือรันด้วยตนเอง:
```powershell
docker-compose -f docker-compose-airflow.yml down
docker-compose -f docker-compose-airflow.yml up -d
```

### 2. ตรวจสอบ Timezone ใน Container
```powershell
docker exec perfect_airflow_webserver date
docker exec perfect_airflow_webserver bash -c 'echo $TZ'
```

### 3. เข้าใช้งาน Airflow UI
- URL: http://localhost:8083
- Username: `admin`
- Password: `admin123`

### 4. ตรวจสอบ DAG Schedule
ใน Airflow UI:
1. ไปที่ DAGs page
2. คลิกที่ DAG ที่ต้องการ
3. ดูที่ "Schedule" และ "Next Run"
4. ตรวจสอบว่าเวลาเป็น Asia/Bangkok

## 📊 การทำงานของระบบ

### เวลา 00:05 น. (เที่ยงคืน)
1. รัน Full Scraping
2. ดึงข้อมูลทั้งหมดจากแหล่งข้อมูล:
   - EPPO Oil Prices (PTT, Shell)
   - Brent Oil Price (FRED)
   - USD/THB Exchange Rate (BOT)
3. บันทึกลง PostgreSQL และ CSV

### เวลา 12:05 น. (เที่ยงวัน)
1. รัน Smart Update
2. ตรวจสอบการเปลี่ยนแปลงข้อมูล
3. อัปเดตเฉพาะข้อมูลที่เปลี่ยน
4. บันทึกลง PostgreSQL และ CSV

## ✅ การยืนยันการตั้งค่า

### ตรวจสอบว่า Timezone ถูกต้อง:
1. **Docker Compose:**
   - ✅ `TZ: 'Asia/Bangkok'` ใน webserver
   - ✅ `TZ: 'Asia/Bangkok'` ใน scheduler
   - ✅ `AIRFLOW__CORE__DEFAULT_TIMEZONE: 'Asia/Bangkok'`

2. **DAG Schedules:**
   - ✅ `'5 0,12 * * *'` = 00:05 และ 12:05
   - ✅ ใช้เวลา Asia/Bangkok

3. **Scraper Logic:**
   - ✅ เช็คชั่วโมง 0 และ 12
   - ✅ ใช้ `datetime.now()` ซึ่งจะเป็น local time ของ container

## 🔍 Troubleshooting

### ถ้า DAG รันไม่ตรงเวลา:
1. ตรวจสอบ timezone ใน container:
   ```powershell
   docker exec perfect_airflow_scheduler date
   ```

2. ตรวจสอบ Airflow config:
   ```powershell
   docker exec perfect_airflow_scheduler airflow config get-value core default_timezone
   ```

3. ดู logs:
   ```powershell
   docker logs perfect_airflow_scheduler
   ```

### ถ้าต้องการเปลี่ยนเวลารัน:
1. แก้ไข `schedule_interval` ใน DAG files
2. แก้ไข `get_current_time_context()` ใน `smart_oil_scraper.py`
3. รีสตาร์ท Airflow

## 📝 หมายเหตุ

- **Cron ใช้เวลา local** ของ Airflow scheduler container
- หลังจากตั้ง `TZ=Asia/Bangkok` แล้ว Cron จะใช้เวลาไทย
- `AIRFLOW__CORE__DEFAULT_TIMEZONE` ใช้สำหรับ UI และ logging
- การเปลี่ยน timezone ต้อง restart containers ทุกครั้ง

## 🎯 สรุป

✅ **ตอนนี้ระบบใช้เวลา Asia/Bangkok แล้ว**
✅ Scraper จะรันเวลา **00:05** และ **12:05 น.** (เวลาไทย)
✅ ไม่ต้องคำนวณ offset UTC อีกต่อไป
