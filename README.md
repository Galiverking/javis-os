# Javis OS

ผู้ช่วยเสียงส่วนตัวภาษาไทย ที่รันอยู่บนเครื่องนี้ (Linux Mint 22.3 / X11 / PipeWire)
ทำหน้าที่เป็น **Precision Voice & Desktop Interface Layer** สั่งงานระบบ สตรีมเสียงโต้ตอบ และส่งต่องานซับซ้อนให้ Hermes Gateway (port 8000)

> สถานะ: **Planning (v0.2 — ปรับแผนสมบูรณ์หลังผ่านการวิเคราะห์ข้อโต้แย้งทางเทคนิค 7 ประการ)**

## เอกสาร

| ไฟล์ | เนื้อหา |
|---|---|
| [docs/PRD.md](docs/PRD.md) | วิสัยทัศน์ ผู้ใช้ use case, Two-Tier Latency และ requirement ฉบับสมจริง (v0.2) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | สถาปัตยกรรม Thread-isolated Audio, Fast-path router, Hermes integration, Hybrid modal (v0.2) |
| [docs/ROADMAP.md](docs/ROADMAP.md) | แผนงาน M0–M4 สโคปสมจริงสำหรับ Solo Developer พร้อมเกณฑ์ Acceptance ชัดเจน (v0.2) |
| [docs/adr/](docs/adr/) | บันทึกการตัดสินใจสำคัญ (ADR-0001 ถึง ADR-0006) พร้อมมติการปรับปรุง (Resolution) |
| [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) | ข้อจำกัดฮาร์ดแวร์จริง (RAM Available ~700MB, Built-in Mic/Speaker AEC, Cinnamon Shortcut) |

## หลักคิด 5 ข้อ (v0.2)

1. **Voice Frontend & Desktop Hands** — Javis โฟกัสที่ Audio Pipeline, Fast-Path คำสั่ง Desktop และส่งต่องานคิดซับซ้อนให้ Hermes Gateway
2. **Two-Tier Latency** — คำสั่งสั้นผ่าน Local Fast Path ได้ P50 ≤ 0.8–1.0s; งานคิดทั่วไปผ่าน Cloud P50 ≤ 2.8s
3. **Hardware-Aware Audio Policy** — ใช้ Intelligent Half-Duplex ป้องกันเสียงสะท้อนเข้าไมค์ (Echo loop) บนลำโพงแล็ปท็อป เว้นแต่จะเสียบหูฟัง
4. **Hybrid Desktop Confirmation** — คำสั่งอันตรายต้องมี Desktop GUI Dialog (`zenity` / notification) ควบคู่เสียง ไม่ฝากชีวิตไว้กับ STT ฝั่งเดียว
5. **Strict Memory & Thread Safety** — Audio C-callback แยก Thread ป้องกัน GIL lock, ห้ามใช้ faster-whisper small ป้องกัน OOM

## ข้อจำกัดที่ออกแบบมาบนเครื่องนี้

- **RAM Available ~0.7 GB** → ปิดกั้นโมเดลใหญ่ถาวร, ควบคุม daemon RSS ≤ 180 MB, ออฟไลน์จำกัดที่ tiny เท่านั้น
- **Built-in Mic & Speaker** → ใช้ Half-Duplex (ปิดไมค์ขณะเล่นเสียง) เพื่อกันเสียงวนลูป, รองรับ PTT interrupt
- **Linux Mint / Cinnamon** → ใช้ Cinnamon Native Shortcuts (`cinnamon-settings shortcuts`) ควบคุม PTT เสถียร 100%
- **Hermes Gateway (port 8000)** → มี Agentic & Memory อยู่แล้ว จึงเชื่อมต่อผ่าน API ไม่เขียนระบบสมองซ้ำซ้อน

## ถัดไป

1. เริ่ม M0 ตาม ROADMAP: scaffold, thread-isolated audio loop, doctor, fakes
2. ติดตั้ง dependency ตาม ENVIRONMENT.md และแมป Cinnamon Shortcut เข้ากับ `javis ptt`
