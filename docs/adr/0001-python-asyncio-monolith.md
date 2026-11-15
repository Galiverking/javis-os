# ADR-0001: Python + asyncio single-process monolith

- สถานะ: Accepted
- วันที่: 2026-11-13

## Context

ต้องรวม audio I/O, VAD, wake word, STT/TTS clients, LLM streaming, tool execution
และ HTTP/WebSocket ไว้ในระบบเดียว บนเครื่อง RAM 5.7 GB ไม่มี GPU
ทีมมีคนเดียว ต้องการ iterate เร็วและ debug ง่าย

## Decision

ใช้ Python 3.12 + `asyncio` เป็น daemon เดียว (`javis daemon`)
แยกโมดูลภายในด้วย Protocol/interface แต่ไม่แยก process หรือ microservice
ยกเว้น tool ที่อาจค้าง (`shell.run`) ให้รันใน subprocess พร้อม timeout

## Consequences

ข้อดี
- latency ต่ำ (ไม่มี IPC ระหว่าง audio → brain → TTS)
- debug ด้วย trace เดียวจบ, deploy ง่าย (systemd unit เดียว)
- ecosystem เสียง/AI ของ Python ครบ

ข้อเสีย
- GIL: งาน CPU หนัก (local STT) ต้องรันใน thread/process แยก
- crash ครั้งเดียวกระทบทั้ง daemon → ต้องมี supervisor และ state ที่ recover ได้
- ไม่เหมาะถ้าอนาคตต้องรองรับผู้ใช้หลายคน/หลายเครื่องพร้อมกัน

## Alternatives

- Node/TypeScript: audio ecosystem อ่อนกว่า, ONNX/wake word ใช้งานยากกว่า
- Rust: เร็วและเบา แต่ development speed ช้ากว่ามากสำหรับ MVP
- แยก service ต่อ provider: latency และ complexity สูงเกินไปสำหรับผู้ใช้คนเดียว

## ข้อโต้แย้ง / แย้งแผน (Critique)

1. **GIL Contention & Audio Buffer Overrun (xrun):** `sounddevice` (PortAudio C-callback) อ่อนไหวต่อ latency ระดับ millisecond หากรันในโปรเซสเดียวกับ FastAPI, JSON serialization และ SQLite I/O อาจเกิดเหตุการณ์ GIL ล็อกจน audio stream ดรอปเฟรม เกิดเสียงป๊อปหรืออัดเสียงขาดช่วง
2. **Crash Domain กว้างเกินไป:** หาก C-library เช่น `onnxruntime` หรือ `portaudio` เกิด segfault ตัว daemon จะตายทันที ทำให้ timers, web dashboard และ CLI ควบคุมเครื่องทั้งหมดดับไปด้วย
3. **ข้อเสนอแนะ:** ยังคงเป็นโมโนลิธได้ แต่ **Audio Pump (Capture/Playback) + VAD ควรแยกเป็น dedicated OS thread หรือ lightweight worker process** โดยสื่อสารผ่าน ring buffer/queue เพื่อไม่ให้ถูก GIL ของ orchestrator บล็อก

✅ **มติการปรับปรุง (ADR-0001 Resolution v0.2):**
- คงความเป็นเดมอนเดียว (Single Service) เพื่อความเรียบง่าย แต่ **แยก Audio I/O Worker (Capture & VAD) ให้อยู่ใน Dedicated OS Thread (C-Safe)**
- ใช้ Ring Buffer และ Thread-safe Queue ส่งข้อมูลเสียงไปยัง Asyncio Orchestrator ป้องกันไม่ให้ GIL และ I/O อื่นๆ บล็อกการทำงานของเสียง
- ปรับปรุง Error Boundary ใน C-wrappers ให้มี Safe Fallback ไม่ให้ segfault ลามสู่กระบวนการหลัก
