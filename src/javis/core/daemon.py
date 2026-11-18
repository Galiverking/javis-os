"""Javis OS Voice Pipeline Orchestrator Daemon.
Orchestrates:
1. PTT Unix Socket Listener (Strict Toggle)
2. Audio Capture + Half-Duplex Isolation
3. Audio UX Chimes & Desktop Notifications
4. Groq Whisper Cloud STT (Thai)
5. Fast-Path Local Command Router (Tier 1 — Regex)
5.5. Tier 1.5 Guardrail + Intent Router (Opt-in via JEV_API_KEY)
6. Hermes Gateway + Gemini 2.5 Flash Free-Tier LLM (Tier 2)
7. Edge-TTS (th-TH-PremwadeeNeural) Speech Playback
"""

import asyncio
import datetime
import io
import logging
import os
import sys
import wave
from enum import Enum
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

from javis.audio.capture import AudioCaptureWorker
from javis.audio.chime import play_error_chime, play_start_chime, play_stop_chime
from javis.audio.half_duplex import HalfDuplexManager
from javis.audio.playback import AudioPlaybackEngine
from javis.config import load_config
from javis.core.router import FastPathRouter
from javis.guardrail.tier15 import Tier15Guardrail
from javis.providers.free_stack import FreeTierLLMClient, FreeTierSTTClient
from javis.tts.edge import EdgeTTSClient
from javis.ui.notify import send_notification

SOCKET_PATH = Path.home() / ".local/share/javis/javis.sock"

def get_dynamic_executive_prompt() -> str:
    """Generate dynamic system prompt with real-time date/time context."""
    now = datetime.datetime.now()
    thai_days = ["วันจันทร์", "วันอังคาร", "วันพุธ", "วันพฤหัสบดี", "วันศุกร์", "วันเสาร์", "วันอาทิตย์"]
    thai_months = [
        "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]
    now_str = f"{thai_days[now.weekday()]}ที่ {now.day} {thai_months[now.month]} พุทธศักราช {now.year + 543} เวลา {now.strftime('%H:%M')} น."

    return (
        f"คุณคือ 'Javis' ผู้ช่วยเสียงส่วนตัวอัจฉริยะภาษาไทย (AI Executive Assistant) ประจำคอมพิวเตอร์ Linux ของเจ้านาย (คุณอภิเชษฐ์)\n"
        f"บริบทเวลาปัจจุบัน: ขณะนี้คือ{now_str}\n"
        f"บุคลิกภาพ: เป็นเลขาผู้ชายที่ฉลาดหลักแหลม มีไหวพริบ สุภาพ กระชับ ฉับไว คล่องแคล่ว ตอบรับชัดเจน\n"
        f"กฎเหล็กการตอบคำถาม:\n"
        f"1. ตอบคำถามอย่างสั้น กระชับ ตรงประเด็นที่สุด (1 ถึง 2 ประโยคเท่านั้น) ไม่ตอบเยิ่นเย้อ\n"
        f"2. ห้ามใช้ markdown, bullet points, หัวข้อย่อย, สัญลักษณ์พิเศษ หรืออิโมจิเด็ดขาด เพราะต้องนำไปสังเคราะห์เสียงพูด\n"
        f"3. ห้ามมีบทเกริ่นนำ ให้ตอบเนื้อหาทันที และลงท้ายด้วย 'ครับ' เสมออย่างสุภาพ\n"
        f"4. สามารถช่วยคิด คำนวณ วิเคราะห์ สรุปความ หรือให้คำแนะนำได้อย่างแม่นยำและฉลาดรอบรู้"
    )


class VoiceState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"


class VoicePipelineOrchestrator:
    """Core state machine managing the voice loop."""

    def __init__(self) -> None:
        self.state = VoiceState.IDLE
        self.half_duplex = HalfDuplexManager()
        self.capture = AudioCaptureWorker(half_duplex=self.half_duplex, sample_rate=16000)
        self.playback = AudioPlaybackEngine(half_duplex=self.half_duplex)
        
        self.config = load_config()
        self.stt = FreeTierSTTClient(api_key=self.config.groq_api_key)
        self.llm = FreeTierLLMClient(api_key=self.config.gemini_api_key)
        self.tts = EdgeTTSClient(voice=self.config.voice)
        self.router = FastPathRouter()
        # Tier 1.5: Opt-in Guardrail + Intent Router (zero RAM overhead)
        self.guardrail = Tier15Guardrail()

        self._audio_buffer: List[bytes] = []
        self._lock = asyncio.Lock()

    def _on_audio_chunk(self, chunk: bytes) -> None:
        """Callback from audio capture thread."""
        if self.state == VoiceState.LISTENING:
            self._audio_buffer.append(chunk)

    async def handle_ptt_toggle(self) -> None:
        """Handle PTT toggle press (Shift+Super)."""
        async with self._lock:
            if self.state == VoiceState.IDLE:
                await self._start_listening()
            elif self.state == VoiceState.LISTENING:
                await self._stop_listening_and_process()
            elif self.state == VoiceState.SPEAKING:
                # Barge-in: interrupt speech and start listening
                self.playback.stop()
                await self._start_listening()
            else:
                # Currently PROCESSING: ignore or chime
                pass

    async def _start_listening(self) -> None:
        """Transition from IDLE to LISTENING."""
        self.state = VoiceState.LISTENING
        self._audio_buffer.clear()
        
        loop = asyncio.get_running_loop()
        # Non-blocking chime in thread
        loop.run_in_executor(None, play_start_chime)
        send_notification("🎙️ Javis กำลังฟัง...", "กด Shift+Super อีกครั้งเพื่อสั่งงาน")
        print("\n🎙️ [Javis] Listening... (Press Shift+Super again to stop)")

        self.capture.start(callback=self._on_audio_chunk)

    async def _stop_listening_and_process(self) -> None:
        """Transition from LISTENING to PROCESSING."""
        self.state = VoiceState.PROCESSING
        self.capture.stop()

        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, play_stop_chime)
        send_notification("⏳ Javis กำลังคิด...", "กำลังถอดเสียงและประมวลผล")
        print("⏳ [Javis] Processing audio...")

        # Spawn asynchronous pipeline task to avoid blocking socket
        asyncio.create_task(self._execute_pipeline())

    def _pcm_to_wav(self, pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
        """Encode raw PCM bytes into WAV in-memory."""
        bio = io.BytesIO()
        with wave.open(bio, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        return bio.getvalue()

    async def process_text_query(self, user_text: str) -> str:
        """Process incoming text query through Tier 1 -> Tier 1.5 -> Tier 2."""
        loop = asyncio.get_running_loop()
        user_text = user_text.strip()
        route_res = self.router.route(user_text)

        if route_res and route_res.matched:
            # ─── Tier 1 Fast-Path matched ───────────────────────────────
            print(f"⚡ [Tier 1 Fast-Path]: {route_res.action}")
            return route_res.speech_response or "ดำเนินการเรียบร้อยครับ"

        # ─── Tier 1.5 Guardrail check ───────────────────────────────
        decision = await loop.run_in_executor(None, self.guardrail.evaluate, user_text)
        mode_tag = "heuristic" if decision.heuristic_only else "LLM-verified"
        print(
            f"🛡️  [Tier 1.5 Guardrail | {mode_tag}] intent={decision.intent} "
            f"allowed={decision.allowed} latency={decision.latency_ms:.0f}ms"
        )

        if not decision.allowed:
            # Blocked by guardrail — refuse, do NOT call Tier 2
            logger.warning("[Daemon] Guardrail BLOCKED: %s", decision.block_reason)
            return (
                "ขออภัยครับ คำสั่งนี้ถูกระบบรักษาความปลอดภัยบล็อกไว้ "
                "เพราะดูเหมือนอาจเป็นอันตรายต่อระบบ"
            )

        # ─── Tier 2: Gemini Flash free-tier ────────────────────
        print("🧠 [Tier 2 Gemini Flash]: Generating answer...")
        reply = await self.llm.generate_response(
            prompt=user_text,
            system_prompt=get_dynamic_executive_prompt(),
        )
        return reply.strip()

    async def _execute_pipeline(self) -> None:
        """Process recorded audio through STT -> Brain -> TTS -> Playback."""
        loop = asyncio.get_running_loop()
        try:
            raw_pcm = b"".join(self._audio_buffer)
            self._audio_buffer.clear()

            # Check if recorded audio is meaningful (> 0.25 seconds)
            if len(raw_pcm) < 16000 * 2 * 0.25:
                print("⚠️ [Javis] Audio too short, cancelled.")
                send_notification("⚠️ Javis", "เสียงสั้นเกินไปครับ")
                await loop.run_in_executor(None, play_error_chime)
                self.state = VoiceState.IDLE
                return

            wav_data = self._pcm_to_wav(raw_pcm, sample_rate=16000)
            try:
                with open("/tmp/javis_last_input.wav", "wb") as f:
                    f.write(wav_data)
            except Exception:
                pass

            duration_sec = len(raw_pcm) / (16000 * 2)
            print(f"  -> Audio recorded: {duration_sec:.1f}s, transcribing with Groq Whisper...")
            user_text = await self.stt.transcribe(wav_data)
            if not user_text or not user_text.strip():
                print("⚠️ [Javis] No speech recognized.")
                send_notification("⚠️ Javis", "ไม่ได้ยินข้อความครับ")
                await loop.run_in_executor(None, play_error_chime)
                self.state = VoiceState.IDLE
                return

            user_text = user_text.strip()
            print(f"🗣️ [User]: \"{user_text}\"")
            send_notification("🗣️ คุณพูด:", user_text, timeout_ms=4000)

            # Process intent through Tier 1 -> Tier 1.5 -> Tier 2
            reply_text = await self.process_text_query(user_text)

            print(f"🤖 [Javis]: \"{reply_text}\"")
            send_notification("🤖 Javis ตอบ:", reply_text, timeout_ms=5000)

            # 3. Speech Synthesis (Edge-TTS)
            print("🔊 [TTS]: Synthesizing speech...")
            mp3_bytes = await self.tts.synthesize_speech(reply_text)

            # 4. Audio Playback with Half-Duplex Protection
            self.state = VoiceState.SPEAKING
            if mp3_bytes:
                await loop.run_in_executor(None, self.playback.play_mp3, mp3_bytes)
            else:
                print("⚠️ [Javis] TTS synthesis failed.")

        except Exception as e:
            print(f"❌ [Javis Error]: {e}")
            send_notification("❌ Javis ขัดข้อง", str(e))
            await loop.run_in_executor(None, play_error_chime)
        finally:
            self.state = VoiceState.IDLE
            print("✨ [Javis] Ready (Idle)\n")


async def run_daemon() -> None:
    """Main daemon server listening for PTT socket signals."""
    SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SOCKET_PATH.exists():
        SOCKET_PATH.unlink()

    orchestrator = VoicePipelineOrchestrator()

    async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            data = await reader.read(128)
            msg = data.decode("utf-8").strip()
            if msg in ("PTT", "PTT_TOGGLE"):
                await orchestrator.handle_ptt_toggle()
                writer.write(b"OK: PTT_TOGGLED\n")
                await writer.drain()
            elif msg == "PING":
                writer.write(b"PONG\n")
                await writer.drain()
            else:
                writer.write(b"ERR: UNKNOWN\n")
                await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_unix_server(_handle_client, path=str(SOCKET_PATH))
    
    # ─── iPhone Mobile Companion Bridge (Port 8765) ─────────────────────
    from javis.ui.mobile_api import MobileCompanionServer
    mobile_server = MobileCompanionServer(orchestrator=orchestrator, host="0.0.0.0", port=8765)
    await mobile_server.start()

    print(f"\n" + "=" * 55)
    print(f"🎙️  Javis OS Voice Assistant (พร้อมรับคำสั่ง)")
    print(f"=" * 55)
    print(f"• คีย์ลัดทั่วเครื่อง: กด Shift + Super เพื่อเปิด/ปิดไมค์")
    if sys.stdin.isatty():
        print(f"• ปุ่มลัดในหน้าต่างนี้: กด [Enter] เพื่อเปิดไมค์พูด / กด [Enter] อีกครั้งเพื่อสั่งงาน!")
    print(f"• Socket: {SOCKET_PATH}")
    print(f"\n📱 iPhone Companion (Safari / Shortcuts / Siri):")
    print(f"   • Wi-Fi ในบ้าน: http://192.168.1.23:8765")
    print(f"   • Tailscale:    http://100.89.142.114:8765")
    print(f"   • Token ลับ:    {mobile_server.token}")
    print("=" * 55 + "\n")
    
    send_notification("🚀 Javis OS พร้อมทำงาน", "กด Shift+Super เพื่อเริ่มคุยได้เลยค่ะ")

    async def _stdin_reader():
        loop = asyncio.get_running_loop()
        while True:
            try:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                await orchestrator.handle_ptt_toggle()
            except Exception:
                break

    stdin_task = None
    if sys.stdin.isatty():
        stdin_task = asyncio.create_task(_stdin_reader())

    try:
        async with server:
            await server.serve_forever()
    finally:
        await mobile_server.stop()
        if stdin_task:
            stdin_task.cancel()
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
