# ADR-0004: Brain เป็น OpenAI-compatible client ที่เราเป็นเจ้าของ tool loop

- สถานะ: Accepted
- วันที่: 2026-11-13

## Context

ต้องการ LLM ที่เรียก tool ได้และภาษาไทยดี ทางเลือก:
1. เรียก `opencode`/`hermes` CLI เป็น black box
2. ใช้ agent framework (LangChain, pydantic-ai, ฯลฯ)
3. เขียน chat-completions client + tool loop เอง

## Decision

เขียน `Brain` เองเป็น client ของ **OpenAI-compatible chat completions**
(รองรับ OpenAI, Groq, OpenRouter, Gemini compat, llama.cpp/Ollama)
tool loop อยู่ใน orchestrator (สูงสุด 6 รอบ) ไม่พึ่ง framework
เก็บ adapter สำหรับ CLI ไว้เป็น "second opinion" ในอนาคต แต่ไม่ใช่เส้นทางหลัก

## Consequences

ข้อดี
- ควบคุม latency และ streaming ได้ละเอียด (จำเป็นต่อ voice)
- เปลี่ยน provider ได้ด้วย `base_url`/`model`
- test ง่าย: fake brain คืน event ตาม script
- ไม่ผูกกับ vendor หรือ CLI ที่เริ่มช้า/มี side effect

ข้อเสีย
- ต้องดูแล tool-call parsing, retry, token counting เอง
- ไม่ได้ความสามารถขั้นสูงของ agent framework (planning, memory) ฟรี
- ต้องรักษา compatibility กับ provider ที่ต่างกันเล็กน้อย

## Alternatives

- CLI as brain: เริ่มช้า (หลายวินาที), ควบคุม tool permission ยาก, output ไม่ streaming
- pydantic-ai/LangChain: เร็วตอนเริ่ม แต่ debug และ tune latency ยากขึ้น; เพิ่ม dependency หนัก
- local LLM: RAM/CPU ไม่พอสำหรับคุณภาพภาษาไทยที่ยอมรับได้

## กติกา

- system prompt และ tool schema ต้องมีเวอร์ชัน (`prompt_version`) เพื่อวัด regression
- tool loop ต้องมีเพดานรอบและเพดาน token
- ถ้า provider ไม่รองรับ tool calling → ใช้ structured JSON fallback (M2)

## ข้อโต้แย้ง / แย้งแผน (Critique)

1. **Reinventing the Wheel ขัดแย้งกับทรัพยากรผู้พัฒนาคนเดียว:** การเขียน Agent Tool Loop, Retries, Policy Engine, Token Budgeting และ Redaction เองตั้งแต่ศูนย์ เป็นการสร้าง Agent Framework ซ้ำซ้อนขึ้นมาใหม่ ทั้งที่ในสภาพแวดล้อมนี้มี **Hermes Gateway (port 8000)** และ agent tooling ที่ใช้งานได้อยู่แล้ว
2. **ขอบเขตบวม (Scope Creep):** จุดขายหลักของ Javis OS คือ **"Voice I/O Layer & Desktop Integration"** การเอาแรงและเวลาไปลงกับการสร้าง Brain Tool Loop ใน M1 จะทำให้การพัฒนา Audio Pipeline ที่ยากและสำคัญกว่าล่าช้า
3. **ข้อเสนอแนะ:** ในช่วงต้นควรออกแบบให้ Brain Adapter สามารถส่ง Intent หรือ Delegate งาน Agent ที่ซับซ้อนไปยัง Hermes Gateway ได้โดยตรง ส่วน Javis OS ถือเฉพาะ Core Desktop Tools สั้นๆ (ปรับเสียง, ปิด-เปิดแอป) ก็เพียงพอ

✅ **มติการปรับปรุง (ADR-0004 Resolution v0.2):**
- **ไม่สร้าง Agent Tool Loop ใหม่ตั้งแต่ศูนย์:** วาง Javis OS เป็น Voice & Desktop Interface Layer
- สำหรับคำสั่งสั้นในเครื่อง: จัดการผ่าน **Local Fast-Path Router** (Volume, Apps, Time, Timer)
- สำหรับคำถามซับซ้อนและงานวิจัย/ค้นหา Obsidian: **เชื่อมต่อกับ Hermes Gateway (port 8000)** ผ่าน REST/HTTP API โดยตรง ซึ่งมี Agent Loop และ Tool System ที่พร้อมใช้อยู่แล้ว
