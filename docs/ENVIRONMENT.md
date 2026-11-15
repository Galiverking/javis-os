# สภาพแวดล้อมที่สำรวจ (2026-11-13)

## เครื่อง

| รายการ | ค่า |
|---|---|
| OS | Linux Mint 22.3 (Ubuntu 24.04 base) |
| Kernel session | X11, desktop X-Cinnamon |
| Python | 3.12.3 (`/usr/bin/python3`) |
| Node | v22.23.0 |
| RAM | 5.7 GiB total — ขณะสำรวจใช้ 5.0 GiB, available ~0.7 GiB |
| GPU | ไม่พบ `nvidia-smi` → assume CPU-only |
| Audio server | PulseAudio 15.0.0 on PipeWire 1.0.5 |
| Capture device | `card 0: PCH [HDA Intel PCH], device 0: 92HD93BXX Analog` |
| Playback | มี `aplay`, default sink 48 kHz stereo |
| ภาษาระบบ | ไทย (ผู้ใช้) |

## เครื่องมือที่มีแล้ว

`arecord`, `aplay`, `pactl`, `wpctl`, `pipewire`, `ffmpeg`, `xdotool`,
`opencode` CLI, `hermes` CLI, `claude` CLI, `gemini` CLI

## Python packages ที่ยังไม่มี (ต้องติดตั้ง)

`sounddevice`, `soundfile`, `fastapi`, `uvicorn`, `httpx`, `pydantic`,
`faster-whisper`, `openwakeword`, `webrtcvad`, `piper-tts`, `edge-tts`,
`pvporcupine`

> แนะนำสร้าง venv แยกที่ `~/.venvs/javis` เพื่อไม่ปนกับ system Python

## สิ่งที่ต้องติดตั้งระดับระบบ

```bash
sudo apt install -y libportaudio2 portaudio19-dev libsndfile1 \
  python3-venv ffmpeg pulseaudio-utils
```

- `libportaudio2` จำเป็นสำหรับ `sounddevice`
- ไม่ต้องติดตั้ง `espeak-ng` (คุณภาพเสียงไทยไม่พอ) — ใช้ edge-tts/piper
- ไม่ต้องใช้ `xbindkeys` — ใช้ `pynput` global hotkey ภายในโปรเซส
  > ⚠️ **ข้อโต้แย้ง / แย้งแผน:** การใช้ `pynput` ดักคีย์ X11 ในระดับโปรเซสมีความเปราะบาง หากหน้าจอล็อก (Screen lock), รันแอป Full-screen หรือมีการเรียกสิทธิ์รูท `pynput` จะหลุดหรือไม่ทำงาน แนะนำให้ใช้ **Cinnamon Native Shortcuts (`cinnamon-settings shortcuts`)** แล้ว map ไปยังคำสั่ง CLI เช่น `javis ptt` หรือส่งสัญญาณ IPC เข้า daemon จะเสถียรและกินทรัพยากรน้อยกว่ามาก
  > 
  > ✅ **มติการปรับปรุง (Environment v0.2):** เปลี่ยนไปใช้ **Cinnamon Native Shortcuts** ผ่าน `cinnamon-settings shortcuts` โดยแมป `Ctrl+Alt+J` ให้เรียก `javis ptt` หรือส่ง IPC signal ตรงเข้า daemon ซึ่งทำงานได้เสถียร 100% แม้ล็อกจอหรือเปิดแอปแบบเต็มจอ

## ข้อจำกัดสำคัญ

1. **RAM เหลือน้อย** — ตอนสำรวจเหลือ ~0.7 GB การรัน local STT (faster-whisper small ≈ 0.5 GB) ทำได้เฉพาะโหมด offline และควรปิดแอปอื่น
  > ⚠️ **ข้อโต้แย้ง / แย้งแผน:** RAM เหลือ 0.7 GB ไม่ใช่แค่เหลือน้อย แต่เข้าขั้นวิกฤต การโหลด `faster-whisper small` (500MB) ร่วมกับ ONNX Runtime และ Python daemon จะทำให้ระบบตกอยู่ในความเสี่ยง OOM Crash สูงมาก ควรปรับเป็น `tiny` เท่านั้นหากต้องออฟไลน์จริง
  > 
  > ✅ **มติการปรับปรุง (Environment v0.2):** กำหนด Daemon Memory Budget RSS $\le 180\text{ MB}$ และแบนโมเดลขนาดใหญ่ทุกตัว หากต้องใช้ออฟไลน์จำกัดที่ `tiny` เท่านั้น
2. **ไม่มี GPU** — local LLM ไม่คุ้ม latency; ใช้ cloud LLM หรือ CLI ที่มีอยู่
3. **ไมโครโฟนในตัว** — คุณภาพและ noise ต้องวัดจริงก่อนตั้งค่า VAD; แนะนำทดสอบอัดเสียง 10 ประโยคไทย
  > ⚠️ **ข้อโต้แย้ง / แย้งแผน:** นอกจาก Noise แล้ว ปัญหาใหญ่ที่สุดของ Built-in Mic คือ **Acoustic Echo** จากลำโพงเครื่องตัวเอง เมื่อเปิดเสียงตอบกลับ ลำโพงจะยิงเสียงเข้าไมค์ตรงๆ ต้องเปิดใช้งาน PipeWire `module-echo-cancel` หรือใช้หูฟัง มิฉะนั้น VAD จะ Loop ตัดเสียงตัวเอง
  > 
  > ✅ **มติการปรับปรุง (Environment v0.2):** ใช้ Intelligent Half-Duplex ปิด Audio Input อัตโนมัติระหว่างที่ Playback กำลังเล่นเสียงออกลำโพงในตัวเครื่อง
4. **Cloud egress** — ต้องมี API key สำหรับ STT/LLM; ทดสอบแล้ว `api.groq.com` และ `api.openai.com` เข้าถึงได้ (ตอบ 401 เมื่อไม่มี key)
5. **มี Hermes gateway รันอยู่** (port 8000, status online) — สามารถใช้เป็นช่องทางแจ้งเตือน/LINE ภายหลังได้ แต่ไม่ใช่ dependency ของ MVP

## แผนทรัพยากร (ประมาณการ)

| Component | RAM | CPU |
|---|---|---|
| Python runtime + orchestrator | 120–180 MB | ต่ำ |
| openWakeWord (ONNX) | 40–70 MB | ~2–5% core |
| VAD (silero/webrtcvad) | 20–40 MB | ต่ำมาก |
| edge-tts | ~50 MB (ไม่ถือ model) | ต่ำ |
| piper th_TH (offline fallback) | 150–250 MB | ~10–20% core ตอนพูด |
| faster-whisper small int8 (offline) | 450–600 MB | 40–90% core |

เป้า runtime ปกติ (cloud STT/TTS edge) ≤ 350 MB
