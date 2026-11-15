# Javis OS — Architecture (v0.2)

## 1. ภาพรวม

Single-process Python asyncio service + plugin-style providers/tools
แยก "สมอง" (LLM) ออกจาก "ปาก/หู" (STT/TTS) และ "มือ" (tools) อย่างชัดเจน

```
┌───────────────────────────── Javis daemon (asyncio) ─────────────────────────────┐
│                                                                                  │
│  Mic ──► Capture(16k mono) ──► VAD ──► Segment ──► STT ──┐                       │
│            ▲                                             ▼                       │
│   Hotkey ──┘                                     Orchestrator (FSM)             │
│   WakeWord ─┘                                            │                       │
│                                                          ├──► Brain (LLM + tools loop)
│                                                          │        │               │
│                                                          │        ▼               │
│                                                          │   Tool Runtime ──► Policy ──► OS/HTTP/DB
│                                                          │        │               │
│                                                          ▼        ▼               │
│  Speaker ◄── Playback(24k) ◄── TTS ◄── Sentence chunker ◄── Response text         │
│                                                                                  │
│  EventBus ──► CLI / WebSocket / Dashboard / Notifications / Audit log            │
└──────────────────────────────────────────────────────────────────────────────────┘
```

หลักการสำคัญ

- **ทุกอย่างเป็น event** (`wake.detected`, `stt.final`, `brain.tool_call`, `tts.first_audio`, ...)
  → CLI/dashboard/automation observe ได้เท่ากัน
- **Orchestrator เป็นที่เดียวที่ถือ state** — provider/tool ไม่รู้จักกัน
- **Stream ตั้งแต่ต้นจนจบ** — LLM token → ประโยค → TTS chunk → playback เพื่อลด latency
- **Tool call เป็น JSON schema** และผ่าน policy engine ก่อนรันเสมอ

> ⚠️ **ข้อโต้แย้ง / แย้งแผนโครงสร้างระบบ (Architecture Critique):**
> 1. **ความเสี่ยง GIL ใน Single-Process Asyncio:** Audio capture และ VAD/WakeWord (ONNX inference) ทำงานแบบ real-time บน CPU หากรันใน asyncio process เดียวกัน ช่วงที่ LLM streaming ประมวลผล JSON/Redaction หรือ SQLite ทำการ sync disk จะเกิด GIL contention ทำให้ Audio thread ใน C (PortAudio) เกิด buffer overrun (xrun) เสียงจะแตก/กระตุก หรือ VAD ตัดคำผิดพลาด **ควรแยก Audio capture & VAD ไปเป็น dedicated worker process/thread อย่างชัดเจน**
> 2. **ความเปราะบางของ Single Process:** หาก C-extensions (PortAudio, ONNX Runtime) เกิด crash หรือ segfault โปรเซสจะล่มทั้งหมด ทำให้ HTTP API, Timers และ CLI ดับตามไปด้วย
>
> ✅ **มติการปรับปรุง (Architecture v0.2 Resolution):**
> - ปรับโครงสร้างเป็น **Thread-Isolated Audio Engine**: แยก PortAudio C-callback และ Silero VAD (ONNX) ให้อยู่ใน Dedicated Worker Thread (C-Safe) มี Ring Buffer อิสระ ไม่ถูก Event Loop ของ asyncio บล็อก ข้อมูลเสียงถูกส่งข้าม Thread ผ่าน Thread-Safe Queue เท่านั้น
> - เพิ่ม **Intelligent Half-Duplex Manager**: ตัดสัญญาณรับเสียงไมค์อัตโนมัติขณะ Playback เล่นเสียงออกลำโพง เพื่อป้องกัน Acoustic Echo Feedback 100% บนลำโพงแล็ปท็อป
> - เชื่อมต่อ **Hermes Gateway (port 8000)** เป็น Agent Brain Backend หลัก เพื่อลดความซ้ำซ้อนในการเขียน Agent Tool Loop เอง

## 2. Component breakdown

| Component | หน้าที่ | หมายเหตุ |
|---|---|---|
| `audio.capture` | เปิด stream 16 kHz mono int16, ring buffer | ใช้ `sounddevice` (PortAudio) |
| `audio.vad` | ตรวจเสียงพูด/ความเงียบ, ตัด segment | Silero VAD (ONNX) เป็นหลัก, webrtcvad fallback |
| `audio.wake` | wake word "hey jarvis" | `openwakeword` (ONNX, local) |
| `audio.worker` | Audio capture & ring buffer (C-safe) | Dedicated OS thread, PortAudio, ป้องกัน GIL |
| `audio.half_duplex` | ควบคุมสลับโหมดไมค์/ลำโพง | ตรวจจับ PipeWire sink/source, auto-mute |
| `audio.hotkey` | global PTT `Ctrl+Alt+J` | Cinnamon Native Shortcut (`cinnamon-settings shortcuts`) |
| `router.fast_path` | ตรวจจับคำสั่งระบบตรงตัว | Regex pattern matcher (Volume, Time, Apps) |
| `client.hermes` | Agent Brain Adapter | คุยกับ Hermes Gateway (`http://localhost:8000`) |
| `policy.hybrid` | ระบบยืนยันความปลอดภัย | Voice confirmation + Desktop Modal (`zenity`) |
| `audio.playback` | เล่น PCM/MP3 stream, รองรับ stop ทันที | `sounddevice` + `ffmpeg -f s16le` pipe |
| `stt.*` | speech → text | Groq / OpenAI / faster-whisper (offline) |
| `tts.*` | text → audio stream | edge-tts (หลัก) / piper (offline) |
| `brain.*` | ตัดสินใจ + เรียก tools | OpenAI-compatible chat completions |
| `tools.*` | action handlers + schema | builtin + plugin manifest |
| `core.orchestrator` | FSM, turn lifecycle, barge-in | หัวใจของระบบ |
| `core.events` | typed pub/sub | asyncio.Queue |
| `memory` | SQLite: sessions/turns/actions/timers/facts | WAL mode |
| `api` | FastAPI REST + WS | bind 127.0.0.1:8787 |
| `cli` | `javis ask/listen/tools/doctor` | Typer |
| `telemetry` | structured logs, turn traces | JSON lines |

## 3. State machine

```
IDLE ──wake/ptt──► LISTENING ──vad.end──► TRANSCRIBING ──text──► THINKING
  ▲                    │                       │                    │
  │                    │ timeout               │ stt.error          │ tool CONFIRM
  │                    ▼                       ▼                    ▼
  │                  ERROR ◄───────────────────┴────────────── CONFIRMING
  │                    │                                            │ yes/no
  │                    └──────────────► IDLE ◄──────────────────────┘
  │                                       ▲
  └──────────── done ◄── SPEAKING ◄────────┘
```

| State | เข้าเมื่อ | ออกเมื่อ | Timeout |
|---|---|---|---|
| IDLE | เริ่มต้น, ตอบจบ | wake word / hotkey / API | — |
| LISTENING | ได้สัญญาณเริ่ม | VAD พบ silence 500–700 ms | 15 s (ตัด), 3 s (ไม่มีเสียง → กลับ IDLE) |
| TRANSCRIBING | มี audio segment | ได้ transcript | 8 s |
| THINKING | มี transcript | ได้คำตอบ หรือ ต้อง confirm tool | 30 s (ยกเว้น tool ยาว) |
| CONFIRMING | tool ระดับ CONFIRM | ผู้ใช้ตอบ yes/no | 8 s → default deny |
| SPEAKING | มี text chunk | playback จบ หรือ barge-in | ตามความยาว |
| ERROR | exception ที่ recover ได้ | แจ้งผู้ใช้แล้ว | — |

Barge-in: ขณะ `SPEAKING` ถ้า wake word/hotkey ถูกตรวจพบ → `playback.stop()` ทันที → `LISTENING`
(ต้องเปิด `barge_in = true`; ใน M1 ปิดไว้ก่อน)

> ⚠️ **ข้อโต้แย้ง / แย้งแผน (Barge-in & Echo):** หากใช้ลำโพงและไมค์ในตัวเครื่อง เมื่อเปิดเสียง TTS ลำโพงจะส่งเสียงเข้าไมค์ตัวเอง (Acoustic Echo) ทำให้ WakeWord หรือ VAD ทริกเกอร์หลอนและตัดเสียงพูดตัวเองทันที หากไม่มี **Acoustic Echo Cancellation (AEC)** (เช่น PipeWire `echo-cancel` หรือ WebRTC AEC) ฟังก์ชัน Barge-in จะใช้งานไม่ได้จริงบนฮาร์ดแวร์นี้ เว้นแต่จะบังคับใช้หูฟัง
>
> ✅ **มติการปรับปรุง (Barge-in v0.2 Resolution):**
> 1. ในโหมดปกติ (ลำโพงแล็ปท็อป) ให้ทำงานแบบ **Intelligent Half-Duplex** (Mute Mic ขณะเล่นเสียง) เพื่อความเสถียรสูงสุด
> 2. อนุญาตให้เปิด Full-Duplex Barge-in เฉพาะเมื่อตรวจพบว่าผู้ใช้เสียบหูฟัง (Headphones) หรือเปิด PipeWire AEC (`module-echo-cancel`)
> 3. รองรับ **Hardware Barge-in (Cancel PTT):** ผู้ใช้สามารถกดปุ่ม Hotkey PTT ซ้ำอีกครั้งเพื่อตัดเสียงพูดของ Javis ได้ทันที

## 4. Turn lifecycle (happy path)

1. `wake.detected` → เล่น chime สั้น → `LISTENING`
2. Capture buffer → VAD ตัด segment → `stt.transcribe`
3. Orchestrator ประกอบ messages: system prompt + facts + 10 turns ล่าสุด + transcript
4. Brain stream: text tokens + tool calls
5. Tool call → policy check → execute → ผลลัพธ์กลับเข้า brain (สูงสุด 6 รอบ)
6. Text ถูกแบ่งเป็นประโยค → TTS synthesize ทีละประโยค → playback ต่อเนื่อง
   > ⚠️ **ข้อโต้แย้ง / แย้งแผน (Sentence Chunker ภาษาไทย):** ในภาษาอังกฤษการตัดประโยคทำได้ง่ายด้วย punctuation (`.!?`) แต่ภาษาไทยไม่มีเครื่องหมายจบประโยคและไม่เว้นวรรคคำ การตัด chunk ส่งให้ edge-tts ขณะ LLM กำลัง stream tokens จึงซับซ้อนมาก หากตัดผิดจังหวะ (เช่น ตัดกลางกลุ่มคำ) เสียงสังเคราะห์จะวรรคแปลก จังหวะสะดุด และสำเนียงเพี้ยน ต้องมีกติกาชัดเจน เช่น รอ punctuation, newlines หรือเว้นวรรค และกำหนด buffer ขนาดขั้นต่ำ (เช่น 20–40 ตัวอักษร) ก่อนส่งสังเคราะห์
>
> ✅ **มติการปรับปรุง (Thai Chunker v0.2 Algorithm):**
> 1. **Minimum Buffer Rule:** สะสมตัวอักษรอย่างน้อย **35–50 ตัวอักษร** ก่อนพิจารณาตัด chunk เพื่อไม่ให้ส่งคำย่อยสั้นเกินไปเข้า edge-tts ซึ่งเสี่ยงต่อการถูก Rate limit และเสียงกระตุก
> 2. **Boundary Detection:** ตัดประโยคเมื่อพบ: Newline (`\n`), เครื่องหมายวรรคตอน (`!`, `?`, `,`), หรือช่องว่างระหว่างคำ (Whitespace) หลังจาก Buffer ครบขนาดขั้นต่ำ
> 3. **Conjunction Awareness:** หากจำเป็นต้องตัดที่ตัวเชื่อม (และ, แต่, หรือ, เพราะว่า) ต้องเว้นวรรคให้ถูกต้องก่อนส่งสังเคราะห์เสียง
7. บันทึก turn/actions/latency → `IDLE`

## 5. Provider interfaces

```python
# stt/base.py
class STTProvider(Protocol):
    name: str
    async def transcribe(self, audio: AudioSegment, *, language: str = "th") -> Transcript: ...
    async def health(self) -> bool: ...

@dataclass
class Transcript:
    text: str
    language: str
    confidence: float | None
    duration_ms: int
```

```python
# tts/base.py
class TTSProvider(Protocol):
    name: str
    async def synthesize(self, text: str, *, voice: str | None = None) -> AsyncIterator[bytes]: ...
    async def health(self) -> bool: ...
```

```python
# brain/base.py
class Brain(Protocol):
    async def respond(
        self, messages: list[Message], tools: list[ToolSpec], *,
        stream: bool = True,
    ) -> AsyncIterator[BrainEvent]: ...

# BrainEvent = TextDelta | ToolCallRequested | TurnFinished | BrainError
```

Provider selection มาจาก config; orchestrator รู้จักแค่ Protocol
ทุก provider ต้องมี fake implementation สำหรับ test (คืน fixture ที่กำหนดได้)

## 6. Tool / action system

```python
class ToolSpec(BaseModel):
    name: str                    # "system.open_app"
    description: str             # ภาษาไทย+อังกฤษ เพื่อให้ LLM เข้าใจ
    params: type[BaseModel]      # JSON schema อัตโนมัติจาก pydantic
    permission: Permission       # SAFE | CONFIRM | DANGEROUS
    timeout_s: float = 10
    handler: Callable[..., Awaitable[ToolResult]]
```

### Permission policy

| ระดับ | พฤติกรรม |
|---|---|
| `SAFE` | รันทันที: เปิดแอป, volume, เวลา, อากาศ, จดโน้ต |
| `CONFIRM` | ถามยืนยันด้วยเสียงก่อน: ปิดแอป, ลบไฟล์, `shell.run` |
| `DANGEROUS` | ปิดใน config โดย default; ต้องเปิด explicit + confirm ทุกครั้ง |

กฎเหล็ก:

1. LLM ไม่สามารถลด permission ของ tool เองได้ — policy เป็นโค้ด ไม่ใช่ prompt
2. ทุก tool call ต้องมี `call_id`, `turn_id` และ audit record
3. `shell.run` รับเฉพาะ argv list (ไม่ผ่าน shell), จำกัด cwd, blocklist คำสั่งอันตราย
4. เนื้อหาจากเว็บ/ไฟล์ถูกครอบด้วย `<untrusted>...</untrusted>` และห้ามตีความเป็นคำสั่ง
5. ถ้า tool ค้างเกิน timeout → kill process group และคืน error ให้ brain

### Builtin tools (MVP)

| Tool | Permission | หมายเหตุ |
|---|---|---|
| `system.get_datetime` | SAFE | เวลา/วันที่/วันในสัปดาห์ |
| `system.open_app` | SAFE | ใช้ `.desktop` lookup + allowlist |
| `system.set_volume` | SAFE | `wpctl set-volume`, step 5% |
| `system.media_control` | SAFE | play/pause/next/prev ผ่าน playerctl |
| `timer.create` / `timer.cancel` / `timer.list` | SAFE | persist ใน SQLite, แจ้งเตือนผ่านเสียง |
| `notes.append` | SAFE | เขียนลง Obsidian vault ที่กำหนด |
| `system.status` | SAFE | CPU/RAM/disk/battery |
| `weather.get` | SAFE | cached 15 นาที |
| `web.search` / `web.fetch` | SAFE (อ่าน) | mark untrusted |
| `system.screenshot` | SAFE | เก็บที่ `~/.local/share/javis/shots` |
| `system.close_app` | CONFIRM | ต้องระบุ process ที่รู้จัก |
| `shell.run` | CONFIRM (ปิด default) | argv allowlist |

## 7. Data model (SQLite)

`~/.local/share/javis/javis.db`, WAL, foreign keys on

```sql
sessions(id TEXT PK, channel TEXT, started_at TEXT, ended_at TEXT)
turns(id TEXT PK, session_id TEXT FK, ts TEXT, role TEXT, text TEXT,
      latency_json TEXT, trace_id TEXT)
actions(id TEXT PK, turn_id TEXT FK, ts TEXT, tool TEXT,
        args_json TEXT, result_json TEXT, permission TEXT,
        status TEXT, approved_by TEXT)
timers(id TEXT PK, label TEXT, due_at TEXT, status TEXT, created_at TEXT)
facts(id TEXT PK, key TEXT, value TEXT, source_turn TEXT, created_at TEXT)
events(id INTEGER PK AUTOINCREMENT, ts TEXT, type TEXT, payload_json TEXT)
```

- `args_json` / `result_json` ผ่าน redactor ก่อนเขียน
- FTS5: `turns_fts(text)` และ `notes_fts(path, content)` (M2+)
- retention: turns 30 วัน (config), events 14 วัน; timers/facts ไม่ลบอัตโนมัติ

## 8. Config

`~/.config/javis/javis.toml` (secrets จาก env/keyring เท่านั้น)

```toml
[general]
language = "th"
data_dir = "~/.local/share/javis"
api_host = "127.0.0.1"
api_port = 8787
log_level = "INFO"
retention_days = 30

[audio]
input_device = "default"
sample_rate = 16000
frame_ms = 20
vad_threshold = 0.5
silence_ms = 600
max_utterance_ms = 15000

[wake]
enabled = true
model = "hey_jarvis"
threshold = 0.5
barge_in = false
hotkey = "ctrl+alt+j"

[stt]
provider = "groq"
model = "whisper-large-v3-turbo"
fallback = ["openai", "local_whisper"]
timeout_s = 8

[tts]
provider = "edge"
voice = "th-TH-PremwadeeNeural"
rate = "+0%"
fallback = "piper"
chunk_sentences = true

[brain]
provider = "openai_compat"
base_url = "https://api.openai.com/v1"
model = "gpt-4o-mini"
max_tool_rounds = 6
temperature = 0.4
timeout_s = 30

[tools]
enabled = ["system.*", "timer.*", "notes.*", "weather.*", "web.*"]
disabled = ["shell.run"]

[privacy]
store_audio = false
redact_patterns = ["sk-*", "Bearer *", "password=*"]
```

## 9. Directory layout

```
javis-os/
├── pyproject.toml
├── README.md
├── docs/
├── config/javis.example.toml
├── scripts/
│   ├── install.sh          # venv + apt deps + symlink CLI
│   └── javis.service       # systemd --user
├── src/javis/
│   ├── cli.py
│   ├── config.py
│   ├── logging.py
│   ├── audio/{capture,playback,vad,wake,hotkey}.py
│   ├── stt/{base,groq,openai,local_whisper,fake}.py
│   ├── tts/{base,edge,piper,fake}.py
│   ├── brain/{base,openai_compat,prompts,fake}.py
│   ├── tools/{registry,policy,builtin/*}.py
│   ├── core/{orchestrator,state,events,session,chunker}.py
│   ├── memory/{db,models,redact}.py
│   └── api/{server,ws}.py
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/audio/     # WAV ไทย 50 ประโยค + hey jarvis samples
```

## 10. Performance budget

| Stage | เป้า P50 | หมายเหตุ |
|---|---|---|
| wake detect | 100 ms | frame 20 ms, ต้อง ≤ 5 frames |
| endpoint (silence) | 600 ms | ปรับได้ตาม noise |
| STT (cloud) | 500–900 ms | ไฟล์ 3–5 วิ, upload+inference |
| LLM first token | 500–1200 ms | ขึ้นกับ provider |
| TTS first chunk | 250–500 ms | edge-tts เร็วกว่า piper cold start |
| **รวม voice-to-voice** | **≤ 2.0 s** | ยังไม่รวมเวลา tool |

> ⚠️ **ข้อโต้แย้ง / แย้งแผน (Reality Check ด้าน Latency):**
> - ตารางนี้คำนวณแบบ Best-Case (600 + 500 + 500 + 250 = 1,850 ms) ซึ่งเกิดขึ้นได้ยากมากในสภาพแวดล้อมจริง
> - การส่ง Audio ผ่านอินเทอร์เน็ตไป Cloud STT มี Network RTT (ไทย-สหรัฐฯ ~200-250ms)
> - โมเดลภาษาไทยใน LLM มักต้องใช้หลาย tokens กว่าจะได้ใจความพอให้ chunker ตัดประโยคแรก (เพิ่มอีก 200–500 ms)
> - เมื่อรวมเวลาเชื่อมต่อ edge-tts ที่เป็น unofficial endpoint จะพบว่าเวลาเฉลี่ย P50 จริงจะอยู่ที่ **2.5 – 3.2 วินาที** (และ $\ge 3.8\text{ s}$ หากมี tool)
>
> ✅ **มติการปรับปรุง (Latency Budget v0.2: Two-Tier Architecture):**
> 1. **Tier 1 (Fast-Path Local Rule Matching):** ข้าม LLM ทั้งหมด สำหรับคำสั่ง Desktop ทั่วไป (ปรับเสียง, วันเวลา, เปิดแอป, ตั้งเวลา) $\rightarrow$ **เป้าหมาย P50 $\le 0.8\text{ s}$, P95 $\le 1.2\text{ s}$**
> 2. **Tier 2 (Cloud Conversational / Hermes Gateway):** คำถามหรือคำสั่งซับซ้อน ปรับเป้าหมายให้สอดคล้องกับสภาพจริง $\rightarrow$ **เป้าหมาย P50 $\le 2.8\text{ s}$, P95 $\le 4.0\text{ s}$**
> 3. **Speculative Chime Masking:** ส่งเสียง Chime ยืนยันสั้นๆ 100ms ทันทีที่ผู้ใช้หยุดพูด เพื่อลด Perceived Latency ระหว่างรอประมวลผล

มาตรการลด latency: stream ทุกช่วง, TTS ทีละประโยค, cache TTS ของข้อความซ้ำ,
pre-warm connection, เล่น chime ระหว่างรอ (mask latency), จำกัด context 10 turns

## 11. Failure handling

| เหตุการณ์ | พฤติกรรม |
|---|---|
| mic ถูกยึด/เปิดไม่ได้ | log + แจ้งเตือนครั้งเดียว + retry ทุก 5 s |
| wake model โหลดไม่ได้ | ปิด wake, ใช้ hotkey, แจ้งใน `doctor` |
| STT timeout/error | ถามให้พูดซ้ำ 1 ครั้ง → กลับ IDLE |
| LLM rate limit | retry แบบ exponential (สูงสุด 2 ครั้ง) → ใช้ข้อความ fallback |
| TTS ล้มเหลว | แสดงข้อความแทนเสียง + log |
| tool error | ส่ง error ให้ brain อธิบายผู้ใช้; ไม่ crash orchestrator |
| network ขาด | ใช้ offline stack (piper + faster-whisper ถ้าติดตั้ง); บอกผู้ใช้ |
| daemon crash | systemd restart; timers โหลดจาก SQLite ใหม่ |

## 12. Security & privacy

- API bind `127.0.0.1` + bearer token สุ่มเก็บ `0600`
- secrets: env/keyring; ห้ามอยู่ใน `javis.toml` หรือ log
- raw audio: ไม่เก็บ; debug capture ต้องเปิด flag ชัดเจนและลบอัตโนมัติใน 24 ชม.
- redaction: regex + key-name based ก่อนเขียน DB/log
- prompt injection: ถือเนื้อหาเว็บ/ไฟล์เป็น data; tools ที่เขียนข้อมูลต้อง confirm
- audit: `actions` table + JSONL append-only ที่ `~/.local/share/javis/audit.jsonl`
- การแจ้งข้อมูลออกนอกเครื่อง: แสดง provider ที่ใช้ใน `javis doctor` และ log ระดับ INFO

## 13. Observability

- structured JSON log ต่อ turn: `trace_id, session_id, state transitions, provider, model, token counts, tool calls, latency breakdown`
- `javis doctor` ตรวจ: mic, speaker, wake model, providers (health), DB, disk, config
- metrics (M3): `/metrics` Prometheus text — counters (turns, errors, wake hits), histograms (latency stages)
- replay: `javis trace <trace_id>` แสดง timeline ของ turn

## 14. Testing strategy

| ระดับ | เครื่องมือ | เนื้อหา |
|---|---|---|
| unit | pytest | policy, chunker, redactor, config, tool handlers (mock OS) |
| provider contract | pytest + fixtures | ทุก provider ต้องผ่านชุดเดียวกัน (fake network) |
| pipeline integration | WAV fixtures | ป้อนเสียง → ได้ข้อความ → เรียก fake brain → ตรวจ tool calls |
| e2e (hardware) | script | อัดเสียงจริง 10 ประโยค, วัด latency, ตรวจ transcript |
| regression | ชุด 50 ประโยคไทย | accuracy ≥ 80% first-shot |
| safety | pytest | tool CONFIRM ต้องไม่รันเมื่อไม่มี approval; injection samples |

CI: `ruff` + `mypy` + `pytest -m "not hardware"`

## 15. Deployment

- `scripts/install.sh`: สร้าง venv `~/.venvs/javis`, ติดตั้ง package, copy config ตัวอย่าง, ตรวจ deps
- `~/.config/systemd/user/javis.service`

```ini
[Unit]
Description=Javis OS voice assistant
After=graphical-session.target pipewire.service
PartOf=graphical-session.target

[Service]
ExecStart=%h/.venvs/javis/bin/javis daemon
Restart=always
RestartSec=3
EnvironmentFile=%h/.config/javis/env

[Install]
WantedBy=graphical-session.target
```

- log → journald; `journalctl --user -u javis -f`
- upgrade: `uv pip install -e .` หรือ git pull + restart (ไม่ต้อง migrate ถ้า schema version เดิม)

## 16. Open technical questions

1. ใช้ Silero VAD ผ่าน `onnxruntime` ตรง ๆ หรือพึ่ง `openwakeword` ที่ bundle มา?
2. TTS streaming: edge-tts คืน MP3 ต่อประโยค — จะ decode ด้วย ffmpeg pipe หรือเล่นผ่าน `mpv`?
3. ต้องการให้ brain เรียก Hermes tools ที่มีอยู่แทนการเขียน tool ใหม่หรือไม่ (ลดงาน แต่ coupling สูง)
4. จะรองรับ Wayland ในอนาคตหรือไม่ (hotkey/overlay ต้องใช้ portal)
