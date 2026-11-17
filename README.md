# Javis OS (v0.3.1)

**Precision Voice & Desktop Interface Layer + iPhone 11 Companion (100% Free Stack)**  
ออกแบบสำหรับ **Linux Mint 22.3 (X11 / PipeWire / Cinnamon)** ภายใต้งบประมาณหน่วยความจำ **`daemon RSS <= 180 MB`** เชื่อมต่อ **Hermes Gateway (port 8000)**, **Life & Study Manager**, และ **iPhone 11 (Tailscale + Shortcuts + Scriptable)**

---

## สถาปัตยกรรมหลัก (3-Tier Pipeline + Tier 1.5 Guardrail)

1. **Zero-Weight Audio & VAD (`src/javis/audio/`):**
   - `AudioCaptureWorker` + `NumpyRMSVAD` (16kHz mono PCM, `block_size=512`, ตัดจบอัตโนมัติเมื่อเงียบครบ `650ms` โดยไม่กิน RAM เพิ่ม)
   - `HalfDuplexManager` (`350ms` cadence gap ป้องกัน Echo loop) + In-memory WAV (`io.BytesIO`, Zero Disk I/O)
   - `GroqWhisperSTT` (`whisper-large-v3-turbo`)
2. **Tier 1 — Deterministic Fast-Path (`src/javis/core/router.py`):**
   - ตอบสนอง `< 0.8s` สำหรับคำสั่งเดี่ยว: เวลา, วันที่ พ.ศ., แบตเตอรี่, RAM/CPU, ปรับเสียง (`wpctl` / `pactl`), เปิดแอป, ค้นเว็บ, และ Life & Study Manager (`briefing` / `timetable`)
3. **Tier 1.5 — Opt-in Guardrail & Intent Router (`src/javis/guardrail/tier15.py`):**
   - Heuristic-only 0ms ป้องกันคำสั่งอันตราย + Opt-in LLM Verification (เมื่อตั้งค่า `JEV_API_KEY`)
4. **Tier 2 — Hermes Gateway & Gemini Tool Loop (`src/javis/brain/hermes.py`, `src/javis/providers/free_stack.py`):**
   - `HermesGatewayClient` (localhost port 8000, Soft Timeout `3.5s`, Circuit Breaker `15s`)
   - Fallback ไปยัง `gemini-2.5-flash` พร้อม JSON Tool-Calling Loop
5. **2-Tier Policy & SQLite Memory (`src/javis/core/policy.py`, `src/javis/core/memory.py`):**
   - คำสั่ง `SAFE` รันทันทีพร้อม HUD `notify-send` / คำสั่ง `SENSITIVE` ยืนยันผ่าน `zenity --question` (Desktop) หรือ `POST /v1/confirm` (iPhone 11)
   - บันทึก Rolling Memory (10 turns) และ `tool_audit_log` ลง `~/.local/share/javis/javis.db`
6. **Streaming Sentence-Chunked TTS (`src/javis/tts/edge.py`):**
   - `ThaiSentenceChunker` + Async Prefetch Queue (`th-TH-NiwatNeural`) + 32-item LRU Micro-Phrase RAM Cache + รองรับ Barge-in

---

## M4.1: iPhone 11 Companion (`src/javis/ui/mobile_api.py`, `mobile/`, `docs/`)

- **Network:** Tailscale Mesh VPN (port `8765`) + Bearer Token (`javis mobile-token`)
- **Endpoints:** `GET /v1/health`, `POST /v1/ask` (คืน `audio_b64` จาก `EdgeTTSClient`), `POST /v1/confirm` (Two-Step Mobile Confirmation)
- **iPhone 11 Setup:** ดูคู่มือ `docs/IPHONE11_SHORTCUTS_GUIDE.md` (Siri, Lock Screen Widget, Cloud Fallback `Speak Text` เมื่อคอมปิด) และวางโค้ด `mobile/javis_widget.js` ในแอป Scriptable

---

## คำสั่ง CLI หลัก (`src/javis/cli.py`)

```bash
javis doctor         # ตรวจความพร้อม RAM, Audio, API Keys, Hermes และเครื่องมือ Linux
javis run            # รัน Voice Daemon + Mobile Companion Bridge (:8765)
javis ptt            # สลับสถานะ Push-To-Talk (ผูกกับ <Shift><Super> บน Cinnamon)
javis ask "ข้อความ"   # สั่งงาน/ถามผ่าน Terminal (เพิ่ม --speak เพื่ออ่านออกเสียง)
javis tools --audit  # แสดงรายการเครื่องมือ, ระดับสิทธิ์ และ Audit Log ล่าสุด
javis calibrate      # วัดระดับเสียงรบกวนเพื่อแนะนำ JAVIS_VAD_RMS_THRESHOLD
javis mobile-token   # แสดง/สร้าง Bearer Token สำหรับ iPhone 11
```

---

## เอกสารอ้างอิง (`docs/`)

| เอกสาร | รายละเอียด |
| :--- | :--- |
| `docs/PRD.md` | Product Requirements & Use Cases (v0.2) |
| `docs/ARCHITECTURE.md` | สถาปัตยกรรมระบบ Thread-isolated Audio, Router, Hermes & Hybrid Modal |
| `docs/ROADMAP.md` | แผนการพัฒนา M0–M4 |
| `docs/ENVIRONMENT.md` | สภาพแวดล้อม Linux Mint 22.3 (RAM ~700MB, Built-in Mic/Speaker, Cinnamon) |
| `docs/IPHONE11_SHORTCUTS_GUIDE.md` | คู่มือตั้งค่า Apple Shortcuts, Siri, Tailscale และ Scriptable บน iPhone 11 |
