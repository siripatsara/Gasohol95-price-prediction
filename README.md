# EPPO Oil Price Scraper

ระบบดึงข้อมูลราคาน้ำมันแก๊สโซฮอล 95 จากเว็บไซต์ EPPO แบบอัตโนมัติ

## 🎯 วัตถุประสงค์

- ดึงข้อมูลราคาน้ำมันแก๊สโซฮอล 95 จาก PTT และ Shell จากเว็บ EPPO
- อัปเดตข้อมูลใน CSV file และฐานข้อมูล PostgreSQL
- รันแบบตั้งเวลาด้วย Airflow
- Forward fill ข้อมูลที่ขาดหาย

## 📊 ข้อมูลที่ดึงมา

- **Date**: วันที่
- **price_PTT**: ราคาแก๊สโซฮอล 95 สถานี PTT
- **price_Shell**: ราคาแก๊สโซฮอล 95 สถานี Shell  
- **effective_date**: วันที่มีผลบังคับใช้

## 🏗️ โครงสร้างโปรเจค

```
perfect/
├── scraper/                    # โค้ด scraping
│   ├── direct_iframe_scraper.py    # Scraper หลักที่ใช้ Selenium
│   └── eppo_oil_scraper.py         # Scraper เดิม (ใช้ requests)
├── dags/                       # Airflow DAGs
│   └── oil_price_scraper_dag.py    # DAG สำหรับรันตั้งเวลา
├── data/                       # ไฟล์ข้อมูล
│   └── only_2_stations.csv         # ข้อมูลราคาน้ำมัน
├── database/                   # Schema ฐานข้อมูล
│   └── schema.sql                  # โครงสร้างตาราง PostgreSQL
├── scripts/                    # สคริปต์ช่วยเหลือ
│   └── load_csv_to_db.py          # โหลดข้อมูล CSV เข้าฐานข้อมูล
├── logs/                       # Log files
├── requirements.txt            # Python dependencies
├── docker-compose-airflow.yml  # Docker setup สำหรับ Airflow
├── setup_airflow.ps1          # Setup script สำหรับ Windows
└── README.md                  # คู่มือนี้
```

## 🚀 การติดตั้งและใช้งาน

### ข้อกำหนดเบื้องต้น

- Python 3.8+
- Chrome Browser (สำหรับ Selenium)
- PostgreSQL (หากต้องการใช้ฐานข้อมูล)

### 1. ติดตั้ง Dependencies

```bash
# ติดตั้ง packages จาก requirements.txt
pip install -r requirements.txt
```

### 2. ทดสอบ Scraper

```bash
# รัน scraper เพื่อทดสอบ
python scraper/direct_iframe_scraper.py
```

### 3. ตั้งค่าฐานข้อมูล (Optional)

```bash
# สร้างตารางในฐานข้อมูล
psql -h localhost -p 5435 -U postgres -d gasohol_prediction -f database/schema.sql

# โหลดข้อมูลจาก CSV เข้าฐานข้อมูล
python scripts/load_csv_to_db.py
```

### 4. ตั้งค่า Airflow (สำหรับรันตั้งเวลา)

```powershell
# รัน setup script
.\setup_airflow.ps1

# หรือใช้ Docker
docker-compose -f docker-compose-airflow.yml up -d
```

## 🔧 การใช้งาน

### รัน Scraper แบบ Manual

```bash
python scraper/direct_iframe_scraper.py
```

### รัน Scraper ผ่าน Airflow

1. เริ่ม Airflow Webserver และ Scheduler:
```bash
airflow webserver --port 8080
airflow scheduler
```

2. เข้า Web UI: http://localhost:8080
   - Username: admin
   - Password: admin123

3. เปิดใช้งาน DAG: `eppo_oil_price_scraper`

### กำหนดการ

- **Schedule**: ทุกวันเวลา 06:00 น.
- **Retry**: 2 ครั้ง หากล้มเหลว
- **Timeout**: 5 นาที

## 📋 Features

### ✅ ความสามารถหลัก

- ✅ ดึงข้อมูลราคาน้ำมันจากเว็บ EPPO
- ✅ รองรับ iframe และ JavaScript content
- ✅ Forward fill ข้อมูลที่ขาดหาย
- ✅ อัปเดต CSV file อัตโนมัติ
- ✅ รองรับฐานข้อมูล PostgreSQL
- ✅ รันตั้งเวลาด้วย Airflow
- ✅ ตรวจสอบคุณภาพข้อมูล
- ✅ สำรองข้อมูลอัตโนมัติ

### 🔄 กระบวนการทำงาน

1. **Scraping**: เข้าไป iframe ของเว็บ EPPO
2. **Parsing**: แยกข้อมูลราคา PTT และ Shell
3. **Validation**: ตรวจสอบความถูกต้องของข้อมูล
4. **Forward Fill**: เติมข้อมูลที่ขาดหายด้วยข้อมูลล่าสุด
5. **Storage**: บันทึกลง CSV และฐานข้อมูล
6. **Backup**: สำรองข้อมูลประจำวัน

## 🐛 การแก้ไขปัญหา

### ปัญหาที่พบบ่อย

**1. ChromeDriver Error**
```bash
# แก้ไข: ติดตั้ง ChromeDriver ใหม่
pip install --upgrade webdriver-manager
```

**2. Database Connection Error**
```bash
# ตรวจสอบ: PostgreSQL running หรือไม่
# เปลี่ยนการตั้งค่าใน scraper/direct_iframe_scraper.py
```

**3. Selenium TimeoutException**
```bash
# เพิ่มเวลา timeout ในไฟล์ scraper
time.sleep(10)  # เพิ่มเวลารอ
```

### Log Files

- **Scraper logs**: ดูใน console output
- **Airflow logs**: `logs/` directory
- **Debug files**: `direct_iframe.html`, `current_page_selenium.html`

## 📈 ตัวอย่างข้อมูล

```csv
Date,price_PTT,price_Shell,effective_date
2025-10-01,32.65,32.65,24 Sep 05:00
2025-10-02,32.65,32.65,24 Sep 05:00
```

## 🔗 Links

- **EPPO Website**: https://www.eppo.go.th/epposite/index.php/th/petroleum/price/oil-price
- **Iframe URL**: https://www.eppo.go.th/epposite/templates/eppo_v15_mixed/eppo_oil/eppo_oil_gen_new.php

## 👥 การพัฒนา

### การเพิ่ม Features ใหม่

1. แก้ไขไฟล์ `scraper/direct_iframe_scraper.py`
2. อัปเดต `dags/oil_price_scraper_dag.py` ถ้าจำเป็น
3. ทดสอบด้วย `python scraper/direct_iframe_scraper.py`

### การเพิ่มสถานีน้ำมันใหม่

1. ศึกษาโครงสร้าง HTML ในไฟล์ `direct_iframe.html`
2. แก้ไข method `parse_oil_price_structure()` 
3. เพิ่ม column ใหม่ใน CSV และฐานข้อมูล

## 📝 License

โครงการนี้ใช้สำหรับการศึกษาเท่านั้น

---

## 📞 สรุป

✅ **สิ่งที่สำเร็จแล้ว:**
- ระบบ scraping ที่ทำงานได้ด้วย Selenium
- ดึงข้อมูลราคาน้ำมันจาก iframe ของเว็บ EPPO
- อัปเดตไฟล์ CSV อัตโนมัติ
- Forward fill ข้อมูลที่ขาดหาย
- Airflow DAG สำหรับรันตั้งเวลา
- ตรวจสอบคุณภาพข้อมูล

🎯 **วิธีใช้งาน:**
1. รัน `python scraper/direct_iframe_scraper.py` เพื่อทดสอบ
2. ตั้งค่า Airflow เพื่อรันตั้งเวลา
3. ข้อมูลจะถูกบันทึกใน `data/only_2_stations.csv`

📋 **ข้อมูลที่ได้:**
- วันที่: 2025-10-02
- ราคา PTT: 32.65 บาท/ลิตร  
- ราคา Shell: 32.65 บาท/ลิตร
- วันที่มีผล: 24 Sep 05:00