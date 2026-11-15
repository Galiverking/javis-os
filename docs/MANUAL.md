# คู่มือการใช้งาน Javis OS (User Manual — Milestone M0 / Voice Pipeline Ready)

ผู้ช่วยเสียงส่วนตัวภาษาไทย บน Linux Mint 22.3 (Cinnamon / PipeWire)  
สถาปัตยกรรม 100% Free Stack (ตามแนวทาง PersonalAIBot-ESP32)

---

## 1. คำสั่งลัดให้เรียกใช้งานง่าย (Symlink CLI)

เพื่อให้เจ้านายพิมพ์คำสั่งสั้นๆ ว่า `javis` ได้จากทุกที่ในเทอร์มินัล:

```bash
mkdir -p ~/.local/bin
ln -sf ~/.venvs/javis/bin/javis ~/.local/bin/javis
```
*(หาก path `~/.local/bin` อยู่ใน `$PATH` แล้ว จะพิมพ์ `javis` ได้ทันที)*

---

## 2. ตั้งค่าปุ่มคีย์ลัด Push-to-Talk (Shift + Super) อัตโนมัติใน 1 คลิก

ระบบมีคำสั่งผูกปุ่มลัด `Shift + Super` บน Linux Mint (Cinnamon) ให้ทันที:

```bash
~/.venvs/javis/bin/javis setup-hotkey
```
*(ระบบจะลงทะเบียนคำสั่ง `Shift + Super` -> `javis ptt` บน Cinnamon ให้เรียบร้อยทันที ไม่ต้องเปิดเมนู Settings เอง)*

---

## 3. วิธีเปิดใช้งาน Javis OS Voice Assistant

### แบบที่ 1: รันสดใน Terminal (Foreground — แนะนำสำหรับทดสอบ)
เปิด Terminal แล้วรันคำสั่ง:
```bash
~/.venvs/javis/bin/javis run
```
- จะมีหน้าต่าง Notification เด้งเตือนว่า **"Javis OS พร้อมทำงาน"**
- ในหน้าจอ Terminal จะแสดง Log การฟังเสียง, การถอดเสียงไทย, คำตอบจาก AI สดๆ ให้เห็นแบบเรียลไทม์
- กด `Ctrl + C` เมื่อต้องการหยุด

### แบบที่ 2: รันเป็น Background Service (เปิดเครื่องมาพร้อมใช้ตลอดเวลา)
```bash
# 1. ติดตั้ง Service ครั้งแรก (ติดตั้งเสร็จจะเปิดใช้อัตโนมัติ)
~/.venvs/javis/bin/javis service install

# 2. เริ่มทำงานเบื้องหลัง
~/.venvs/javis/bin/javis service start

# 3. ตรวจสอบสถานะการทำงาน
~/.venvs/javis/bin/javis service status

# 4. หยุดการทำงาน
~/.venvs/javis/bin/javis service stop
```

---

## 4. วิธีการสั่งงานด้วยเสียง (Strict Toggle Voice UX)

1. **เริ่มสั่งงาน:** กดปุ่ม **`Shift + Super`** (ปุ่มรูปธง Windows) บนคีย์บอร์ดพร้อมกัน 1 ครั้ง
   - จะได้ยินเสียงสัญญาณ Chime ติ๊ง! (880Hz -> 1175Hz)
   - หน้าจอจะขึ้น Notification มุมขวาล่าง: `🎙️ Javis กำลังฟัง...`
2. **พูดคำสั่งหรือคำถาม:** พูดภาษาไทยได้ตามธรรมชาติ เช่น:
   - *"กี่โมงแล้ว"*
   - *"ลดเสียงลงหน่อย"*
   - *"วันนี้อากาศที่เชียงใหม่เป็นยังไงบ้าง"*
   - *"ช่วยอธิบายวิธีทำต้มยำกุ้งสั้นๆ หน่อย"*
3. **จบประโยคและส่งประมวลผล:** กดปุ่ม **`Shift + Super`** ซ้ำอีก 1 ครั้ง
   - จะได้ยินเสียงสัญญาณ Chime ตึ๊ง! (880Hz -> 587Hz)
   - หน้าจอจะขึ้น Notification: `⏳ Javis กำลังคิด...`
   - ระบบจะถอดเสียงผ่าน Groq Whisper ส่งต่อ Gemini 2.5 Flash และเล่นเสียงน้องเปรมวดี (`th-TH-PremwadeeNeural`) ตอบกลับทันที!

---

## 5. ตารางสรุปคำสั่ง CLI ทั้งหมด

| คำสั่ง | การทำงาน |
|---|---|
| `javis run` | รัน Voice Pipeline Daemon ใน Terminal แสดง Log สด |
| `javis setup-hotkey` | ตั้งค่าปุ่มลัด `Shift+Super` บน Cinnamon อัตโนมัติ |
| `javis doctor` | ตรวจสอบสุขภาพระบบ (RAM, ไมค์, ลำโพง, Free API Keys, Linux Tools) |
| `javis ptt` | ส่งสัญญาณจำลองการกดคีย์ลัด PTT |
| `javis test-voice` | ทดสอบเสียงพูดจาวิสเสียงผู้ชาย (`th-TH-NiwatNeural` หรือระบุ `--voice`) |
| `javis service install` | ติดตั้ง systemd user service ให้รันเบื้องหลังอัตโนมัติ |
| `javis service start` | สั่งเปิด service เบื้องหลัง |
| `javis service status` | ตรวจสอบสถานะ service เบื้องหลัง |
| `javis service stop` | สั่งปิด service เบื้องหลัง |

---

## 6. การสลับเสียงพูดและช่องทางเสียง (Voice & Audio Output)

- **เปลี่ยนเสียงพูด (Voice Model):** สามารถระบุเสียงใน `~/.config/javis/env` ผ่านตัวแปร `JAVIS_VOICE`:
  - เสียงผู้ชาย (ค่าเริ่มต้น): `JAVIS_VOICE=th-TH-NiwatNeural`
  - เสียงผู้หญิง (เปรมวดี): `JAVIS_VOICE=th-TH-PremwadeeNeural`
- **สลับช่องทางเสียง (Audio Output Routing):**
  - ลำโพงบลูทูธ (เช่น SP07): `wpctl set-default <bluetooth_sink_id>`
  - ลำโพงตัวเครื่องแล็ปท็อป: `wpctl set-default <builtin_sink_id>`

---

## 7. การทดสอบความถูกต้องของระบบ (Automated Quality Gate)

```bash
cd /home/apichet/for-hermes/01_projects/javis-os
~/.venvs/javis/bin/pytest tests/ -v
```
*(ผลตรวจ: 11/11 tests passed 100% ครอบคลุม Half-Duplex, Chimes, Audio Capture, Fast-Path Router, Free LLM & STT, Life Manager)*
