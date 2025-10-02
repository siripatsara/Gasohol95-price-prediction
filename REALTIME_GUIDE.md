# 📊 Real-time Oil Price Scraping System

## 🎯 ภาพรวมระบบ

ระบบ scraping ราคาน้ำมันแบบ real-time ที่รวบรวมข้อมูลจาก 4 แหล่งหลัก:

### 📁 ไฟล์ข้อมูล

1. **`data/only_2_stations.csv`** - ไฟล์หลักที่มีข้อมูลทั้งหมด (เก่า + ใหม่)
2. **`data/realtime_scraped_data.csv`** - ไฟล์ real-time (เฉพาะข้อมูลตั้งแต่ 3 Oct 2025)

### 🔧 Scrapers

| Scraper | แหล่งข้อมูล | ข้อมูลที่ได้ | ความถี่อัพเดต |
|---------|-------------|-------------|---------------|
| `direct_iframe_scraper.py` | EPPO iframe | PTT, Shell Gasohol 95 | Daily |
| `brent_oil_scraper.py` | FRED | Brent crude oil | Weekly |
| `bot_usd_thb_scraper.py` | BOT | USD/THB exchange | Daily |
| `eppo_levy_scraper.py` | EPPO Excel | Oil Fund Levy | Weekly |

## 🚀 การใช้งาน

### 1. รัน Scrapers ทั้งหมด
```bash
python run_all_scrapers.py
```

### 2. ดูสรุปข้อมูล Real-time
```bash
python run_all_scrapers.py --summary
```

### 3. ดูข้อมูลล่าสุด N วัน
```bash
python run_all_scrapers.py --view 7    # ดู 7 วันล่าสุด
python run_all_scrapers.py --view 30   # ดู 30 วันล่าสุด
```

### 4. รัน Scraper แยกตัว
```bash
python scraper/direct_iframe_scraper.py      # EPPO oil prices
python scraper/brent_oil_scraper.py          # Brent oil
python scraper/bot_usd_thb_scraper.py        # USD/THB
python scraper/eppo_levy_scraper.py          # Oil Fund Levy
```

### 5. จัดการข้อมูล Real-time
```bash
python scraper/realtime_data_manager.py     # ทดสอบ/ซิงค์ข้อมูล
```

## 📊 โครงสร้างข้อมูล

```
Date,price_PTT,price_Shell,effective_date,Price_Brent,USD_BATH,Price_Levy
2025-10-03,32.65,32.65,24 Sep 05:00,66.87,32.19,3.0
```

### คำอธิบายคอลัมน์:
- **Date**: วันที่ scrape ข้อมูล
- **price_PTT**: ราคา Gasohol 95 ที่ปั๊ม PTT (บาท/ลิตร)
- **price_Shell**: ราคา Gasohol 95 ที่ปั๊ม Shell (บาท/ลิตร)
- **effective_date**: วันที่มีผลของราคาน้ำมัน
- **Price_Brent**: ราคาน้ำมันดิบ Brent (USD/บาร์เรล)
- **USD_BATH**: อัตราแลกเปลี่ยน USD/THB
- **Price_Levy**: ภาษีกองทุนน้ำมัน Gasohol 95 (E10) (บาท/ลิตร)

## 🔄 Logic การทำงาน

### Forward-fill Logic
- **Brent Oil**: ใช้ข้อมูลล่าสุดจาก FRED (อาจล่าช้า 1-2 วัน)
- **USD/THB**: ใช้ข้อมูลล่าสุดจาก BOT (ไม่ real-time)
- **Oil Fund Levy**: ใช้ข้อมูลล่าสุดจาก EPPO Excel (อัพเดตสัปดาห์ละครั้ง)

### Historical Validation
- ตรวจสอบการเปลี่ยนแปลงข้อมูลย้อนหลัง
- แก้ไขข้อมูลเก่าอัตโนมัติเมื่อมีการอัพเดต

### File Management
- **EPPO Excel**: เก็บแค่ 2 ไฟล์ (current/previous)
- **ลบไฟล์เก่า**: หลังเปรียบเทียบเสร็จ
- **Real-time File**: เก็บเฉพาะข้อมูลตั้งแต่ 3 Oct 2025

## 📅 Scheduling (Airflow)

ไฟล์ DAG: `dags/oil_price_scraper_dag.py`

```python
# รันทุกวันเวลา 06:00 UTC (13:00 ICT)
schedule_interval='0 6 * * *'
```

## 🔍 Monitoring

### Log Files
- `logs/integrated_scraper.log` - log หลักของระบบ
- `logs/realtime_data_manager.log` - log การจัดการข้อมูล real-time
- `logs/eppo_levy_scraper.log` - log EPPO levy scraper

### ตัวอย่าง Log สำคัญ
```
2025-10-03 06:00:01 - INFO - Excel file has been updated
2025-10-03 06:00:02 - INFO - Found 1 historical changes
2025-10-03 06:00:02 - INFO - 2025-08-20: 2.8 -> 2.9
2025-10-03 06:00:03 - INFO - Updated realtime data for 2025-10-03
```

## 🛠️ Troubleshooting

### ปัญหาทั่วไป

1. **Chrome WebDriver ล้าสมัย**
   ```bash
   # webdriver-manager จะอัพเดตอัตโนมัติ
   ```

2. **เว็บไซต์เปลี่ยนโครงสร้าง**
   - ตรวจสอบ debug HTML files ในโฟลเดอร์หลัก
   - แก้ไข selector ใน scraper code

3. **ข้อมูล Real-time หาย**
   ```bash
   python scraper/realtime_data_manager.py  # ซิงค์ข้อมูลใหม่
   ```

4. **Excel ดาวน์โหลดไม่ได้**
   - ตรวจสอบ URL: https://www.eppo.go.th/epposite/images/Energy-Statistics/energyinformation/Energy_Statistics/Petroleum_Prices/P06.xls
   - ตรวจสอบ network connectivity

## ⚠️ ข้อควรระวัง

1. **Rate Limiting**: ไม่ควรรันบ่อยเกินไป (วันละครั้งพอ)
2. **Data Consistency**: ตรวจสอบข้อมูลผิดปกติ
3. **Error Handling**: ระบบจะข้าม error และดำเนินการต่อ
4. **File Permissions**: ต้องมีสิทธิ์เขียนไฟล์ในโฟลเดอร์ data/

## 📈 การขยายระบบ

### เพิ่ม Scraper ใหม่
1. สร้างไฟล์ scraper ใหม่ใน `scraper/`
2. integrate กับ `RealtimeDataManager`
3. เพิ่มใน `run_all_scrapers.py`

### เพิ่มคอลัมน์ข้อมูล
1. แก้ไข `RealtimeDataManager.init_realtime_file()`
2. อัพเดต scrapers ที่เกี่ยวข้อง
3. ทดสอบ backward compatibility

---

🎉 **ระบบพร้อมใช้งาน!** สำหรับคำถามเพิ่มเติม ดู log files หรือติดต่อ developer