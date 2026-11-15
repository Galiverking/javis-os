# Javis OS — Product Requirements Document (v0.2)

> เจ้าของ: Apichet · สถานะ: Approved Plan (v0.2 — ปรับปรุงตาม Reality Check 7 ประการ) · วันที่: 2026-11-14

## 1. ปัญหา

งานประจำวันบนเครื่องกระจายอยู่หลายที่: เปิดแอป ตั้งเวลา จดโน้ต ค้นข้อมูล ควบคุมเสียง/สื่อ
การสลับหน้าต่างและพิมพ์คำสั่งซ้ำ ๆ กินเวลาและ interrupt งานหลัก
ผู้ช่วยที่มีอยู่ (แชทเว็บ) มองไม่เห็นเครื่อง ไม่รู้บริบท และสั่งงานระบบไม่ได้

## 2. วิสัยทัศน์

> "พูดคำเดียว แล้วงานเสร็จ" — ผู้ช่วยเสียงภาษาไทยที่อยู่บนเครื่อง ตอบเร็ว สั่งงานได้จริง
> จำบริบทได้ และไม่ทำให้ข้อมูลส่วนตัวรั่วโดยไม่ตั้งใจ

Javis OS ทำหน้าที่เป็น **Precision Voice & Desktop Interface Layer** ที่เชื่อมเสียง → ความเข้าใจ → การกระทำบนเครื่อง โดยเชื่อมโยงกับ Hermes Gateway (port 8000) สำหรับงานประมวลผลขั้นสูง

## 3. กลุ่มผู้ใช้

ผู้ใช้คนเดียว: เจ้าของเครื่อง (นักพัฒนา/ผู้ใช้ทั่วไปที่พูดไทย) ใช้งานที่โต๊ะทำงาน มีไมโครโฟนในตัว
ไม่ต้องรองรับ multi-user, multi-tenant ใน v1

## 4. หลักการออกแบบ

1. **Voice-first, CLI-parity** — ทุก action เรียกผ่าน CLI/API ได้เท่ากับเสียง
2. **Two-Tier Latency** — คำสั่งสั้นผ่าน Fast-path ได้ผลทันที (P50 ≤ 0.8s), คำสั่งคิดทั่วไปผ่าน Cloud (P50 ≤ 2.8s)
3. **ยืนยันก่อนทำลาย (Hybrid Modal)** — action อันตรายต้องมี Desktop GUI Modal (`zenity` / popup) ยืนยันควบคู่เสียง
4. **Hardware-Aware Audio Policy** — ใช้ Half-duplex บนลำโพงแล็ปท็อปเพื่อตัดปัญหา Acoustic Echo ขาดลอย
5. **Re-use, Don't Re-invent** — สั่งงาน OS ด้วย builtin tools สั้นๆ และ delegate งานคิดซับซ้อนให้ Hermes Gateway (port 8000)
6. **Observable & Traceable** — ทุก turn มี trace: transcript, intent, tool calls, latency, errors

## 5. Use cases

| ID | สถานการณ์ | ผลลัพธ์ | เส้นทางประมวลผล |
|---|---|---|---|
| UC-01 | "Javis เปิด VS Code" | เปิดแอปภายใน 1.0 วิ | Tier 1: Local Fast-Path |
| UC-02 | "ช่วยหาข่าว AI วันนี้ให้หน่อย" | สรุปสั้น 3–5 บรรทัด พร้อมแหล่ง | Tier 2: Hermes Gateway Web Search |
| UC-03 | "ตั้งเวลา 10 นาที" | มีเสียงยืนยัน + แจ้งเตือนเมื่อครบ | Tier 1: Local Timer Tool |
| UC-04 | "เสียงดังไป ลดหน่อย" | ลด volume 10% | Tier 1: Local Fast-Path (P50 ≤ 0.8s) |
| UC-05 | "จดไว้ใน Obsidian ว่า..." | append โน้ตพร้อม timestamp | Tier 1 / Hermes Obsidian |
| UC-06 | "เมื่อกี้ฉันถามอะไรไปนะ" | ดึงบทสนทนาย้อนหลังได้ | Tier 1: Local SQLite History |
| UC-07 | "ค้นโค้ดโปรเจกต์นี้และวิเคราะห์บั๊ก" | ส่งต่อให้ Hermes Gateway จัดการ | Tier 2: Hermes Gateway Port 8000 |
| UC-08 | "ปิดเครื่อง / ลบไฟล์งานชั่วคราว" | เด้ง GUI Modal ให้คลิกยืนยัน | Tier 1: Hybrid Confirm Policy |

## 6. Functional requirements

ระดับความสำคัญ: **M** = must (MVP), **S** = should, **C** = could

### 6.1 Voice interaction

- **FR-01 (M)** Cinnamon Native Hotkey (`Ctrl+Alt+J`) สั่ง Push-To-Talk (PTT) ผ่าน IPC สู่ daemon ได้เสถียร 100%
- **FR-02 (M)** ตรวจจับจุดจบประโยคด้วย Silero VAD ภายใน ≤ 500–600 ms หลังหยุดพูด
- **FR-03 (M)** ถอดเสียงภาษาไทยผ่าน Groq Cloud STT (`whisper-large-v3-turbo`)
- **FR-04 (S)** Wake word "Hey Javis" (openWakeWord) เป็นฟีเจอร์ทดลอง (Secondary) ปรับเกณฑ์ความคาดหวังให้สมจริง
- **FR-05 (M)** Barge-in & Echo Policy (v0.2):
  - *Default (Built-in Speaker):* Intelligent Half-Duplex (Mute Mic ขณะเล่นเสียง TTS) เพื่อป้องกันเสียงวนลูป (Acoustic Feedback) เด็ดขาด
  * *Barge-in Activation:* เปิด Full-Duplex เมื่อตรวจพบหูฟัง (Headset) หรือเปิด PipeWire `module-echo-cancel` (AEC3)
  * *Hardware Cancel:* กดปุ่ม Hotkey ซ้ำเพื่อสั่ง Interrupt หยุดเสียงพูดทันที
- **FR-06 (M)** ตอบด้วยเสียงไทยผ่าน edge-tts พร้อม Thai Sentence Chunker (Buffer ขั้นต่ำ 35–50 ตัวอักษร) ไม่สะดุดกลางคำ
- **FR-07 (C)** เลือกเสียง (ชาย/หญิง) และความเร็วได้ผ่าน config

### 6.2 Understanding & memory

- **FR-08 (M)** Two-Tier Intent Routing:
  - *Tier 1 Fast-Path:* คำสั่งระบบตรงตัว (เปิดแอป, ปรับเสียง, วันเวลา, ตั้งเวลา) ตัดสินใจใน Local Regex ทันที
  - *Tier 2 Deep Task:* คำถามหรือสั่งงานยาว ส่งต่อให้ Hermes Gateway (port 8000)
- **FR-09 (M)** จำบทสนทนาปัจจุบันอย่างน้อย 10 turn ใน SQLite
- **FR-10 (M)** ถามย้อนหลังใน session ได้ ("เมื่อกี้พูดว่าอะไร")
- **FR-11 (S)** จำข้อเท็จจริงถาวรที่ผู้ใช้สั่ง ("จำไว้ว่า...") ผ่าน SQLite หรือ Hermes Memory
- **FR-12 (C)** ค้นหาประวัติด้วย SQL `LIKE` หรือ FTS5 พร้อม Thai Word Tokenizer

### 6.3 Actions (tool calling)

- **FR-13 (M)** Local Core Tools: `open_app`, `set_volume`, `media_control`, `create_timer`, `append_note`, `get_time_date`
- **FR-14 (M)** Action Confirmation Policy (v0.2):
  - คำสั่งอันตราย (`shell.run`, `delete_file`, `shutdown`, `kill_process`) ต้องใช้ **Hybrid Confirmation**:
    1. ส่งเสียงเตือนถามสั้นๆ
    2. ยิง Desktop GUI Modal ผ่าน `zenity --question` หรือ Cinnamon Notification Action ให้เห็นคำสั่งชัดเจนและกดปุ่มยืนยันได้ทันที
- **FR-15 (M)** ทุก action มี audit log (เวลา, ชื่อ tool, args ที่ redact, ผลลัพธ์, ผู้อนุมัติ)
- **FR-16 (S)** Complex Tools (Web Search, Deep Notes Search, Code Agent) ส่งต่อให้ Hermes Gateway ผ่าน API
- **FR-17 (S)** System status (`cpu`, `ram`, `disk`, `battery`) ผ่านคำสั่งระบบโดยตรง

### 6.4 Interfaces & operations

- **FR-18 (M)** CLI: `javis ask "..."`, `javis ptt`, `javis tools`, `javis doctor`
- **FR-19 (M)** IPC Socket / Local HTTP API (`127.0.0.1:8787`)
- **FR-20 (S)** Dashboard แสดง state, transcript, latency แบบ real-time
- **FR-21 (S)** `systemd --user` autostart และ restart on failure พร้อม memory limit
- **FR-22 (C)** ส่ง notification แจ้งเตือนเมื่อ timer ครบ

## 7. Non-functional requirements (v0.2)

| ด้าน | เป้าหมาย (v0.2 Realistic) | หมายเหตุ |
|---|---|---|
| Latency: Fast-path Commands | **P50 ≤ 0.8 s**, P95 ≤ 1.2 s | ปรับเสียง, ถามเวลา, สั่งเปิดแอป (Local Regex) |
| Latency: Cloud Conversational | **P50 ≤ 2.8 s**, P95 ≤ 4.0 s | VAD 500ms + Groq STT + LLM/Hermes + edge-tts |
| Wake word false reject (TH) | ≤ 15–20% | สำเนียงไทยบนโมเดลอังกฤษ (Hotkey เป็น primary) |
| Wake word false accept | ≤ 1 ครั้ง / 4 ชั่วโมงเงียบ | |
| RAM (idle runtime) | **≤ 180 MB** (Peak ≤ 250 MB) | เครื่องมี RAM เหลือ 0.7GB, ห้าม OOM เด็ดขาด |
| CPU (idle) | ≤ 5% ของ 1 core | C-Safe background thread |
| Crash recovery | service กลับมาภายใน 5 s, SQLite WAL | |
| Security & Safety | Hybrid Confirm (GUI Modal) สำหรับคำสั่งเสี่ยง | ป้องกัน STT mishearing |
| Offline Capability | คำสั่งพื้นฐาน (Fast-path) ทำงานได้ 100% | ไม่ต้องพึ่งพาเน็ตสำหรับ Desktop actions |

## 8. Out of scope (v1)

- Multi-user / authentication หลายบัญชี
- Mobile app / hardware satellite
- โหลด Local LLM หรือ Whisper small ลงเครื่องเด็ดขาด (RAM ไม่พอ)
- เขียนระบบ Agent Framework เองใหม่ทับซ้อนกับ Hermes Gateway

## 9. ตัวชี้วัดความสำเร็จ

1. ใช้งานจริง ≥ 5 คำสั่ง/วัน เป็นเวลา 2 สัปดาห์ติด
2. Fast-path ทำงานถูกต้อง ≥ 95% ภายใน ≤ 1.0 วินาที
3. ไม่มีเหตุการณ์ action อันตรายรันโดยไม่ผ่าน Desktop Confirmation Modal
4. ไม่มีปัญหาเสียง TTS สะท้อนเข้าไมค์ (Echo loop) ในระหว่างใช้งานลำโพงแล็ปท็อป
5. Daemon ไม่เคยถูก Linux OOM Killer ยิงทิ้งตลอดการทดสอบ 7 วัน
