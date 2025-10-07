# เพิ่มการตรวจสอบ USD/THB Historical Rates ใน Afternoon Task

## 🎯 วัตถุประสงค์
เพิ่มการตรวจสอบความถูกต้องของข้อมูล USD/THB ในฐานข้อมูลโดยเปรียบเทียบกับข้อมูล Historical Foreign Exchange Rates บนเว็บธนาคารแห่งประเทศไทย

## 📊 ปัญหาที่แก้ไข
- เว็บธนาคารไม่ได้อัปเดต USD/THB ทุกวัน
- เราใช้ **filled forward** สำหรับวันที่เว็บไม่อัปเดต
- ต้องการตรวจสอบว่าเมื่อเว็บมีการอัปเดต ข้อมูลของเราตรงกับเว็บหรือไม่

## 🔄 การทำงานใหม่ใน Afternoon Task

### 1. **ขั้นตอนเดิม** (ยังคงเหมือนเดิม):
```
1. เปรียบเทียบข้อมูลบ่าย vs ข้อมูลเช้า
2. ตรวจสอบการเปลี่ยนแปลง 5 fields
```

### 2. **ขั้นตอนใหม่** - USD/THB Historical Verification:
```python
# 4.5. ตรวจสอบความถูกต้องของ USD/THB historical rates
for days_back in range(1, 6):  # 5 วันย้อนหลัง
    check_date = datetime.now() - timedelta(days=days_back)
    
    # ดึงข้อมูลจาก database
    db_usd_rate = scraper.get_usd_rate_from_db(date_str)
    
    # ดึงข้อมูลจากเว็บธนาคาร 
    web_usd_rate = scraper.get_historical_usd_rate_from_web(date_str)
    
    # เปรียบเทียบและประเมิน
    if both_available:
        rate_diff = abs(db_rate - web_rate)
        is_accurate = rate_diff <= 0.05  # tolerance 0.05 บาท
```

### 3. **การจัดการกรณีต่างๆ**:

#### ✅ **กรณี Web มีอัปเดต + DB มีข้อมูล**
```
เปรียบเทียบ → ถ้าต่างกัน < 0.05 บาท = ACCURATE
                ถ้าต่างกัน >= 0.05 บาท = DISCREPANCY
```

#### 📝 **กรณี Web ไม่อัปเดต + DB ใช้ Filled Forward**
```
สถานะ: "Web not updated" - ใช้ filled forward ได้ (ปกติ)
```

#### ❌ **กรณี Missing Data**
```
สถานะ: "Data unavailable" - ต้องตรวจสอบ
```

## 📊 ผลลัพธ์ที่ได้

### 1. **Verification Summary**
```json
{
  "total_days_checked": 5,
  "valid_comparisons": 4,
  "accurate_rates": 4,
  "accuracy_percentage": 100.0,
  "discrepancies_found": 0,
  "results": [...]
}
```

### 2. **รายละเอียดแต่ละวัน**
```json
{
  "date": "2025-10-03",
  "db_rate": 32.6137,
  "web_rate": 32.6137,
  "difference": 0.0000,
  "is_accurate": true,
  "status": "accurate"
}
```

### 3. **XCom Variables เพิ่มเติม**
- `usd_verification_result`: ผลการตรวจสอบ USD/THB
- เพิ่มใน `scraping_result['usd_verification']`

## 🔍 การแสดงผลใน Log

```
🔍 Verifying USD/THB Historical Rates...
✅ 2025-10-05: DB=32.6137, Web=32.6137 (diff: 0.0000) - ACCURATE
📝 2025-10-04: Web data not updated - DB: 32.6137, Web: None
✅ 2025-10-03: DB=32.6137, Web=32.6137 (diff: 0.0000) - ACCURATE
✅ 2025-10-02: DB=32.5700, Web=32.5726 (diff: 0.0026) - ACCURATE

📊 USD/THB Historical Verification Summary:
   Total Days Checked: 5
   Valid Comparisons: 4
   Accurate Rates: 4/4
   Accuracy: 100.0%
   ✅ All historical rates are accurate!
```

## 🎯 ประโยชน์

### 1. **Data Quality Assurance**
- ตรวจสอบความถูกต้องของข้อมูล USD/THB
- ยืนยันว่า filled forward strategy ทำงานถูกต้อง

### 2. **Transparency**
- รู้ว่าวันไหนเว็บอัปเดต วันไหนไม่อัปเดต
- มี logs ชัดเจนสำหรับ debugging

### 3. **Proactive Monitoring**
- ตรวจจับ discrepancies ได้เร็ว
- ป้องกันการใช้ข้อมูลผิด

## 🔧 Technical Implementation

### API Methods ที่ต้องมีใน EPPOOilScraper:
```python
# ดึงข้อมูล USD/THB จาก database
scraper.get_usd_rate_from_db(date_str)

# ดึงข้อมูล USD/THB จากเว็บธนาคาร (historical)
scraper.get_historical_usd_rate_from_web(date_str)
```

### Logic Flow:
```
Afternoon Task (13:00) →
├─ เปรียบเทียบกับ morning data
├─ ตรวจสอบ USD/THB historical rates (ใหม่!)
├─ สร้างผลลัพธ์รวม
└─ ตัดสินใจ downstream tasks
```

## ✅ Summary
การเพิ่มฟีเจอร์นี้ทำให้ afternoon task มีความสมบูรณ์มากขึ้น โดยไม่เพียงแค่ตรวจสอบการเปลี่ยนแปลงเฉพาะวันนี้ แต่ยังตรวจสอบคุณภาพข้อมูล USD/THB ย้อนหลังด้วย ช่วยให้มั่นใจได้ว่าข้อมูลที่ใช้มีความถูกต้องและเชื่อถือได้!