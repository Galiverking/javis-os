# Javis OS — Roadmap (v0.2)

> แนวทาง: ส่งของที่ใช้ได้จริงทุก milestone, วัดผลด้วย acceptance criteria ไม่ใช่ความรู้สึก

## M0 — Foundation (0.5–1 วัน)

**เป้าหมาย:** พิสูจน์ว่า audio pipeline บนเครื่องนี้ทำงาน และวางโครงทดสอบได้

- [ ] scaffold `pyproject.toml`, `src/javis/`, ruff + mypy + pytest
- [ ] config loader (`javis.toml` + env override) และ structured logging
- [ ] `audio.capture` + `audio.playback` บันทึก/เล่น WAV 16 kHz
- [ ] provider fakes (STT/TTS/Brain) + contract tests
- [ ] `javis doctor` เวอร์ชันแรก (mic, speaker, disk, config)
- [ ] `scripts/install.sh` สร้าง venv

**Acceptance**
- `javis doctor` ผ่านทุกข้อบนเครื่องนี้
- อัดเสียง 3 วิ แล้วเล่นกลับได้
- `pytest` เขียวทั้งหมด (ไม่ใช้ hardware)

## M1 — MVP Voice Loop (3–5 วัน)

**เป้าหมาย:** พูดสั่งงานจริงได้ 6 อย่าง ผ่านการกด hotkey

- [ ] global hotkey `Ctrl+Alt+J` + push-to-talk
- [ ] Silero VAD + endpointing (silence 600 ms)
- [ ] STT ไทยผ่าน Groq (`whisper-large-v3-turbo`) + timeout/retry
- [ ] Brain: OpenAI-compatible streaming + tool loop (สูงสุด 6 รอบ)
- [ ] tools: `get_datetime`, `open_app`, `set_volume`, `media_control`, `timer.create`, `notes.append`
- [ ] tool policy (SAFE/CONFIRM) + audit log + redaction
- [ ] TTS ไทยผ่าน edge-tts + เล่นทีละประโยค
- [ ] CLI: `javis ask`, `javis listen`, `javis tools`
- [ ] SQLite: sessions/turns/actions/timers

**Acceptance**
- ชุดทดสอบ 20 คำสั่งไทย ทำงานถูก ≥ 16 ครั้งในครั้งแรก
- voice-to-voice P50 ≤ 2.5 s (cloud) บนเครื่องนี้
- ไม่มี action ใดรันโดยไม่มี audit record
- ปิด/เปิด daemon ใหม่แล้ว timer ที่ค้างยังอยู่

> ⚠️ **ข้อโต้แย้ง / แย้งแผน M1:**
> - กรอบเวลา 3–5 วัน สำหรับการทำ Audio Capture + VAD Endpointing + Groq STT + Custom Tool-Calling Engine + SQLite Memory + 6 Tools + Streaming TTS Chunker เป็นการประเมินที่ **Optimistic เกินจริงมาก** สำหรับนักพัฒนาคนเดียว เฉพาะการดีบักปัญหาเสียง (Buffer underrun, Thread synchronization, ALSA/PulseAudio latency) มักกินเวลาไปแล้ว 2–3 วัน
>
> ✅ **มติการปรับปรุง (M1 v0.2 Scope):**
> 1. โฟกัส 100% ที่ Audio Pipeline, VAD, Groq STT และ Intelligent Half-Duplex
> 2. ใช้ **Fast-Path Regex/Rule Matching** สำหรับคำสั่ง Desktop สั้นๆ (Volume, Datetime, App launch, Timer) แทนการเขียน Agent Engine เอง
> 3. เป้าหมาย Latency สำหรับ Fast-Path คือ P50 $\le 0.8\text{ s}$

## M2 — Wake Word & Conversation (3–5 วัน)

**เป้าหมาย:** เรียกด้วยเสียงได้ ไม่ต้องกดปุ่ม และคุยต่อเนื่องได้

- [ ] openWakeWord "hey jarvis" + tuning threshold
- [ ] barge-in (หยุดพูดเมื่อถูกเรียก)
- [ ] multi-turn memory 10 turns + `javis why` (ดู trace)
- [ ] confirm flow ทางเสียง (yes/no, timeout → deny)
- [ ] timers แจ้งเตือนด้วยเสียง + notification fallback
- [ ] noise calibration command (`javis calibrate`)

**Acceptance**
- wake word ทำงานระยะ 1–3 m อัตราถูก ≥ 90% ใน 50 ครั้ง
- false accept ≤ 1 ครั้ง / 4 ชม. ในห้องเงียบ
- barge-in หยุดเสียงภายใน 300 ms
- confirm flow ปฏิเสธเมื่อไม่ตอบภายใน 8 s

> ⚠️ **ข้อโต้แย้ง / แย้งแผน M2:**
> - เกณฑ์ Acceptance Wake Word $\ge 90\%$ จาก 50 ครั้งบนสำเนียงไทยเป็นไปไม่ได้สำหรับโมเดลสำเร็จรูป `hey_jarvis` ของ openWakeWord ซึ่งฝึกด้วย Native English (โอกาสผ่านจริงน่าจะอยู่ที่ 50–70%)
> - ฟังก์ชัน Barge-in จะล้มเหลวทันทีหากเปิดลำโพงแล็ปท็อปโดยไม่มี AEC (Acoustic Echo Cancellation) ใน M2 นี้ควรบังคับทดสอบด้วยการเสียบหูฟังเท่านั้นก่อน
>
> ✅ **มติการปรับปรุง (M2 v0.2 Scope):**
> 1. ปรับเกณฑ์ Wake Word Acceptance ให้สมจริงกับสำเนียงไทยเป็น $\ge 70-80\%$ และลดเป็นฟีเจอร์ทดลอง (Secondary) โดยยึด Hotkey PTT เป็นหลัก
> 2. เชื่อมต่อ **Hermes Gateway (port 8000)** สำหรับประมวลผลคำถามซับซ้อน (Multi-turn conversational & agentic tools)
> 3. ทำงานแบบ Half-Duplex (ปิดไมค์ขณะเล่นเสียง) เป็นค่าเริ่มต้น และเปิด Full-Duplex เฉพาะเมื่อเสียบหูฟัง

## M3 — Daily Driver (1 สัปดาห์)

**เป้าหมาย:** ใช้ทุกวันได้จริง เห็นสถานะ และกู้ปัญหาเองได้

- [ ] Web dashboard + WebSocket events (localhost:8787)
- [ ] `web.search` / `web.fetch` + untrusted wrapping
- [ ] `weather.get`, `system.status`, `system.screenshot`
- [ ] Obsidian notes integration + FTS5 search
- [ ] `systemd --user` autostart + restart policy
- [ ] retention/cleanup job + `javis trace`
- [ ] `/metrics` (Prometheus) พื้นฐาน

**Acceptance**
- dashboard เห็น state/transcript/latency แบบ real-time
- service รอดจากการ kill และกลับมาภายใน 10 s
- ค้นโน้ตเก่าแล้วตอบพร้อมอ้างอิงไฟล์ได้
- ใช้งานจริง 5 คำสั่ง/วัน ติดกัน 7 วันโดยไม่ crash

## M4 — Productize (1–2 สัปดาห์)

- [ ] offline mode: piper th_TH + faster-whisper tiny (opt-in)
- [ ] plugin manifest + hot-reload tools
- [ ] overlay สถานะมุมจอ (X11)
- [ ] แจ้งเตือนผ่าน Hermes gateway (LINE/Telegram)
- [ ] `shell.run` แบบ argv allowlist (CONFIRM ทุกครั้ง)
- [ ] custom wake word (ถ้าต้องการคำอื่น)
- [ ] benchmark dashboard + regression suite 50 ประโยค

**Acceptance**
- ตัดเน็ตแล้วยังสั่งงานพื้นฐาน (เปิดแอป/เวลา/timer/เสียง) ได้
- plugin ใหม่เพิ่มได้โดยไม่แก้ core และมี test
- ไม่มี regression ด้าน latency เกิน 15%

> ⚠️ **ข้อโต้แย้ง / แย้งแผน M4:**
> - สเปก Offline mode ที่เลือก `faster-whisper tiny` จะต้องโหลดโมเดลขนาด ~500MB ลง RAM ขณะที่เครื่องเหลือ Available RAM เพียง ~700MB มีความเสี่ยงวิกฤตที่จะเกิด **OOM Kill หรือ Swap Thrashing** จนเครื่องค้าง
>
> ✅ **มติการปรับปรุง (M4 v0.2 Scope):**
> 1. **แบน faster-whisper tiny โดยเด็ดขาด**
> 2. จำกัด Offline STT ไว้ที่ `faster-whisper tiny` (int8 quantized ~150MB) หรือ Vosk Thai เล็กเท่านั้น
> 3. ปรับสเปกในเช็คลิสต์ M4 ให้เป็น `faster-whisper tiny`

## Backlog (ยังไม่จัดลำดับ)

- ปฏิทิน/อีเมล, task จาก Linear/Notion
- สั่งงานเครื่องอื่นในบ้าน (satellite)
- mobile bridge / Siri Shortcut
- speaker identification (แยกเสียงเจ้าของ)
- สรุปประจำวันอัตโนมัติ + daily briefing
- semantic memory (sqlite-vec) เมื่อ RAM พอ

## Definition of Done (ทุก milestone)

1. feature ทำงานตาม acceptance และมี test ที่รันได้โดยไม่ต้องใช้ hardware (หรือมี hardware marker)
2. documentation/config อัปเดต
3. ไม่มี secret ใน log/DB
4. latency ที่วัดได้ถูกบันทึกใน `docs/BENCHMARKS.md`
5. `javis doctor` ยังผ่าน

## ประมาณการต้นทุน (cloud mode)

| รายการ | ราคา | การใช้จริงโดยประมาณ |
|---|---|---|
| Groq STT whisper-large-v3-turbo | ~$0.04 / ชม.เสียง | 5 นาที/วัน ≈ $0.003/เดือน |
| LLM (gpt-4o-mini class) | ~$0.15 / 1M input tokens | 100 turns/วัน ≈ $0.5–2/เดือน |
| edge-tts | ฟรี | — |

> ตัวเลขเป็นเพียงประมาณการ ต้องวัดจริงหลัง M1

## ความเสี่ยงและมาตรการ

| ความเสี่ยง | ผลกระทบ | มาตรการ |
|---|---|---|
| RAM เหลือน้อย | local STT ใช้ไม่ได้ | cloud-first; offline เป็น opt-in; ปิดโมเดลเมื่อไม่ใช้ |
| ไมโครโฟนในตัว noise สูง | STT แม่นน้อย | calibrate noise floor, VAD tuning, แนะนำหูฟัง |
| Thai STT ผิดคำเฉพาะ | งานผิด | prompt bias ด้วยคำศัพท์ผู้ใช้, แสดง transcript ให้แก้ในโหมด confirm |
| Cloud latency/rate limit | ช้า/ล้ม | timeout + fallback provider + chime mask |
| Tool อันตราย | ความเสียหาย | policy ในโค้ด, confirm, audit, ปิด default |
| Prompt injection จากเว็บ | สั่งงานแปลก | untrusted wrapper + tool permission + ไม่ auto-run |

## แผนสัปดาห์แรก (แนะนำ)

| วัน | งาน |
|---|---|
| 1 | M0: scaffold, audio loop, doctor, fakes |
| 2 | STT + VAD + hotkey + CLI ask |
| 3 | Brain + tool loop + 3 tools + audit |
| 4 | TTS + 3 tools ที่เหลือ + memory |
| 5 | benchmark, แก้ latency, ชุดทดสอบ 20 คำสั่ง, เขียน BENCHMARKS.md |
