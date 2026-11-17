# iPhone 11 Companion — Apple Shortcuts Guide (Javis OS)

คู่มือสรุปขั้นตอนการตั้งค่า Apple Shortcuts เพื่อใช้งาน **Javis OS** ผ่านเสียง, Widget (`mobile/javis_widget.js`), Siri และ Lock Screen บน iPhone 11

---

## สิ่งที่ต้องเตรียมก่อนตั้งค่า

1. **Tailscale IP & Port**: ไอพีของเครื่อง Javis Server (เช่น `100.x.y.z:8765`)
2. **Mobile Token**: `JAVIS_MOBILE_TOKEN` สำหรับยืนยันตัวตนใน Header `Authorization: Bearer <TOKEN>`
3. **Cloud Fallback URL (ทางเลือก)**: URL ของ Google Apps Script (`GAS_BRIEFING_URL`) กรณีเครื่องหลักออฟไลน์

---

## ขั้นตอนการสร้าง Shortcut ชื่อ `Ask Javis`

> **หมายเหตุ:** ตั้งชื่อ Shortcut ว่า `Ask Javis` เพื่อให้ปุ่ม `🎙️ Ask Javis` บน Scriptable Widget (`shortcuts://run-shortcut?name=Ask%20Javis`) เรียกใช้งานได้ทันที

### 1. รับคำสั่งเสียง (`Dictate Text`)
1. เปิดแอป **Shortcuts** บน iPhone แล้วกด `+` เพื่อสร้าง Shortcut ใหม่ ตั้งชื่อว่า **`Ask Javis`**
2. เพิ่ม Action **`Dictate Text`**
   - ตั้งค่า Language เป็นภาษาที่ใช้งาน (เช่น `Thai (Thailand)` หรือ `English`)
   - ตั้งค่า Stop Listening เป็น `After Pause`

### 2. ส่งคำสั่งไปยัง Javis OS (`POST /v1/ask`)
1. เพิ่ม Action **`Get Contents of URL`**
2. ตั้งค่า URL: `http://<TAILSCALE_IP>:8765/v1/ask`
3. กด `Show More` แล้วตั้งค่า:
   - **Method**: `POST`
   - **Headers**:
     - `Content-Type`: `application/json`
     - `Authorization`: `Bearer <YOUR_JAVIS_MOBILE_TOKEN>`
   - **Request Body**: `JSON`
     - `query` (Text): เลือกตัวแปร **`Dictated Text`** จากขั้นตอนที่ 1
     - `tts` (Boolean): `true` (หรือ `false` หากต้องการใช้การอ่านเสียงของ iOS)

### 3. ตรวจสอบการยืนยันคำสั่งสำคัญ (`POST /v1/confirm`)
หาก Javis OS ส่งค่ากลับมาว่าต้องยืนยันการดำเนินการ (เช่น `requires_confirmation: true` พร้อม `confirm_id`):
1. ใช้ Action **`Get Dictionary Value`** เพื่อดึงค่า `requires_confirmation` และ `reply` จากผลลัพธ์ JSON
2. เพิ่มเงื่อนไข **`If`** (`requires_confirmation` is `true`):
   - แสดงข้อความถามผู้ใช้ด้วย **`Ask for Input`** หรือ **`Choose from Menu`** (`ยืนยัน` / `ยกเลิก`)
   - หากผู้ใช้เลือก **ยืนยัน**:
     - เพิ่ม Action **`Get Contents of URL`** ไปที่ `http://<TAILSCALE_IP>:8765/v1/confirm`
     - **Method**: `POST`
     - **Headers**: `Content-Type: application/json`, `Authorization: Bearer <YOUR_JAVIS_MOBILE_TOKEN>`
     - **Request Body** (`JSON`): `{ "confirm_id": "<confirm_id>", "approved": true }`

### 4. เล่นเสียงตอบกลับ (`EdgeTTS` / Cloud Fallback `Speak Text`)
1. **กรณีเซิร์ฟเวอร์ออนไลน์ (EdgeTTS)**:
   - หาก `/v1/ask` หรือ `/v1/confirm` ส่งคืนไฟล์เสียงหรือ URL เสียงจาก EdgeTTS (เช่น `audio_url` หรือ base64 audio):
   - ใช้ **`Get Contents of URL`** ดึงไฟล์เสียง แล้วใช้ Action **`Play Sound`** เพื่อเล่นเสียงทันที
2. **กรณี Cloud Fallback / อ่านข้อความตอบกลับ (`Speak Text`)**:
   - หากไม่มีไฟล์เสียงจาก EdgeTTS หรือเชื่อมต่อเครื่องหลักไม่ได้ (Fallback ไปยัง GAS / ข้อความข้อความสำรอง)
   - ดึงค่า `reply` (หรือ `summary`) ด้วย **`Get Dictionary Value`**
   - ใช้ Action **`Speak Text`** เพื่อให้อุปกรณ์ iPhone อ่านคำตอบออกเสียงอัตโนมัติ

---

## การเรียกใช้งานผ่าน Siri และ Lock Screen

### เรียกผ่าน Siri
- เพียงพูดว่า **"Hey Siri, Ask Javis"** (หรือ **"หวัดดี Siri, Ask Javis"**) ระบบจะเปิด `Dictate Text` และส่งคำสั่งไปยัง Javis OS โดยอัตโนมัติ

### เรียกผ่าน Lock Screen & Home Screen
1. **Lock Screen Widget**:
   - กดค้างที่หน้าจอ Lock Screen -> **Customize** -> **Lock Screen** -> แตะกรอบ Widget
   - เพิ่ม Widget ของแอป **Shortcuts** แล้วเลือก **`Ask Javis`** หรือใช้ **Scriptable Widget** (`mobile/javis_widget.js`) เพื่อดูสรุปงานและกดปุ่ม `🎙️ Ask Javis`
2. **Back Tap (ทางเลือกเสริมบน iPhone 11)**:
   - ไปที่ **Settings** -> **Accessibility** -> **Touch** -> **Back Tap** -> เลือก **Double Tap** หรือ **Triple Tap** แล้วผูกกับ Shortcut **`Ask Javis`**
