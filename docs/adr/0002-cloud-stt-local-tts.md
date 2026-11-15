# ADR-0002: Cloud STT + local/edge TTS (hybrid)

- สถานะ: Accepted
- วันที่: 2026-11-13

## Context

เครื่องมี RAM จำกัดและไม่มี GPU แต่ผู้ใช้ต้องการความแม่นภาษาไทยและ latency ต่ำ
- local Whisper small ใช้ RAM ~0.5 GB และช้ากว่า realtime บน CPU เครื่องนี้
- TTS ไทย local (piper) เบา (~60–250 MB) และไม่ต้องส่งข้อความออกนอกเครื่อง
- edge-tts ให้เสียงไทยธรรมชาติกว่า แต่ต้องต่อเน็ตและส่งข้อความไป Microsoft

## Decision

- **STT:** cloud เป็นค่าเริ่มต้น (Groq `whisper-large-v3-turbo`, fallback OpenAI)
  และมี `local_whisper` เป็น offline opt-in
- **TTS:** edge-tts เป็นค่าเริ่มต้น, piper `th_TH` เป็น offline fallback
- ทั้งสองชั้นอยู่หลัง Protocol เดียวกัน เปลี่ยนได้ด้วย config โดยไม่แตะ orchestrator

## Consequences

ข้อดี
- latency และคุณภาพภาษาไทยดีกว่า local-only อย่างชัดเจน
- RAM ต่ำ, ไม่ต้องโหลด model ตอน start
- ยังมีเส้นทาง offline สำหรับคำสั่งพื้นฐาน

ข้อเสีย
- ต้องมีอินเทอร์เน็ตและ API key สำหรับคุณภาพเต็ม
- เสียงและข้อความบางส่วนออกนอกเครื่อง → ต้องแจ้งผู้ใช้และทำ redaction
- edge-tts เป็นบริการที่ไม่รับประกัน SLA (unofficial endpoint) → ต้องมี fallback

## Alternatives

- local-only (faster-whisper + piper): ช้าและเปลือง RAM เกินไปสำหรับ default
- ใช้ OS dictation/อื่น: ควบคุมไม่ได้และผูกกับ desktop environment

## ข้อโต้แย้ง / แย้งแผน (Critique)

1. **`local_whisper` เสี่ยงทำเครื่องค้าง (OOM Thrashing):** เครื่องมี RAM available เหลือเพียง ~700 MB การอนุญาตให้เปิด `faster-whisper small` (ใช้ RAM ~500-600MB) เป็น offline opt-in มีโอกาสสูงมากที่จะถูก Linux OOM killer ยิงทิ้งทันที หรือทำให้ OS สว็อปจนระบบค้าง
2. **edge-tts เสี่ยงต่อการถูก Block/Throttle:** `edge-tts` พึ่งพา undocumented endpoint ของ Microsoft Edge Online Speech หากส่งถี่ๆ หรือส่งเป็นประโยคย่อยสั้นๆ หลาย chunk อาจเจอ Rate limit/Captcha
3. **ข้อเสนอแนะ:** Offline STT ควรจำกัดขนาดสูงสุดไว้ที่ `faster-whisper tiny` เท่านั้น และต้องเตรียม Local rule-based command parser ไว้สำหรับคำสั่งพื้นฐานโดยไม่ต้องพึ่ง STT เต็มรูปแบบ

✅ **มติการปรับปรุง (ADR-0002 Resolution v0.2):**
- **แบน faster-whisper small ออกจากสเปกโดยเด็ดขาด** จำกัดโหมดออฟไลน์ไว้ที่ `faster-whisper tiny` (int8) หรือ Vosk Thai ขนาดเล็ก เพื่อรักษา RAM ให้อยู่ในระดับปลอดภัย
- นำ **Fast-path Local Rule Matching** มาใช้สำหรับคำสั่ง Desktop พื้นฐาน (ไม่เรียก STT/LLM ภายนอก)
- สำหรับ `edge-tts` ให้ควบคุมการตัดกลุ่มคำ (Sentence Chunker) ด้วยขนาด Buffer ขั้นต่ำ 35–50 ตัวอักษร เพื่อไม่ให้ส่งคำขอย่อยถี่เกินไปจนเสี่ยงถูก Rate limit
