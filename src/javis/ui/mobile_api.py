"""Lightweight Asyncio HTTP Mobile Companion Bridge for iPhone (Apple Shortcuts + Scriptable + Safari Web UI)."""
import asyncio
import base64
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("javis.mobile_api")


def get_or_create_mobile_token() -> str:
    env_tok = os.getenv("JAVIS_MOBILE_TOKEN", "").strip()
    if env_tok:
        return env_tok
    tok_file = Path.home() / ".config" / "javis" / "mobile_token"
    if tok_file.exists():
        return tok_file.read_text(encoding="utf-8").strip()
    tok_file.parent.mkdir(parents=True, exist_ok=True)
    new_tok = secrets.token_urlsafe(24)
    tok_file.write_text(new_tok, encoding="utf-8")
    return new_tok


_MOBILE_HTML_PAGE = """<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Javis OS — iPhone Companion</title>
  <link rel="apple-touch-icon" href="https://fav.farm/🤖">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <style>
    :root {
      --bg: #090d16;
      --card: rgba(22, 28, 45, 0.75);
      --card-border: rgba(255, 255, 255, 0.1);
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.3);
      --text: #f1f5f9;
      --text-muted: #94a3b8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
    body {
      background: radial-gradient(circle at 50% 0%, #1e293b 0%, var(--bg) 80%);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      padding: 16px;
    }
    header {
      text-align: center;
      padding: 12px 0 16px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
      font-size: 12px;
      font-weight: 600;
      padding: 4px 12px;
      border-radius: 9999px;
      margin-bottom: 8px;
    }
    .dot { width: 8px; height: 8px; background: #34d399; border-radius: 50%; box-shadow: 0 0 8px #34d399; }
    h1 { font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }
    p.sub { font-size: 13px; color: var(--text-muted); margin-top: 2px; }

    .chat-box {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      padding: 12px 0;
      margin-bottom: 12px;
    }
    .msg {
      max-width: 85%;
      padding: 12px 16px;
      border-radius: 18px;
      font-size: 15px;
      line-height: 1.45;
      word-break: break-word;
    }
    .msg.user {
      align-self: flex-end;
      background: linear-gradient(135deg, #0284c7, #2563eb);
      color: white;
      border-bottom-right-radius: 4px;
    }
    .msg.javis {
      align-self: flex-start;
      background: var(--card);
      border: 1px solid var(--card-border);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      color: var(--text);
      border-bottom-left-radius: 4px;
    }
    .quick-chips {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 8px;
      scrollbar-width: none;
    }
    .quick-chips::-webkit-scrollbar { display: none; }
    .chip {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--card-border);
      color: var(--text);
      font-size: 13px;
      padding: 6px 14px;
      border-radius: 9999px;
      white-space: nowrap;
      cursor: pointer;
    }
    .controls {
      display: flex;
      gap: 8px;
      align-items: center;
      background: var(--card);
      border: 1px solid var(--card-border);
      padding: 8px;
      border-radius: 24px;
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
    }
    input[type="text"] {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      color: white;
      font-size: 16px;
      padding: 8px 12px;
    }
    button.icon-btn {
      width: 44px;
      height: 44px;
      border-radius: 50%;
      border: none;
      background: var(--accent);
      color: #04101e;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      cursor: pointer;
      box-shadow: 0 0 12px var(--accent-glow);
      transition: transform 0.1s;
    }
    button.icon-btn:active { transform: scale(0.92); }
    button.mic-btn {
      background: rgba(255, 255, 255, 0.1);
      color: white;
      box-shadow: none;
    }
    button.mic-btn.recording {
      background: #ef4444;
      color: white;
      animation: pulse 1.2s infinite;
    }
    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
      70% { box-shadow: 0 0 0 14px rgba(239, 68, 68, 0); }
      100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
    .footer-note {
      text-align: center;
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 8px;
    }
  </style>
</head>
<body>
  <header>
    <div class="badge"><div class="dot"></div> เชื่อมต่อ Javis OS แล้ว</div>
    <h1>🤖 Javis Companion</h1>
    <p class="sub">สั่งการด้วยเสียงและข้อความจาก iPhone 11</p>
  </header>

  <div class="chat-box" id="chat">
    <div class="msg javis">สวัสดีครับเจ้านาย! Javis พร้อมรับคำสั่งจาก iPhone แล้วครับ สามารถพิมพ์หรือกดไอคอนไมค์เพื่อพูดได้เลยครับ 🎙️</div>
  </div>

  <div class="quick-chips">
    <div class="chip" onclick="quickSend('ตอนนี้กี่โมงแล้ว')">⏰ กี่โมงแล้ว</div>
    <div class="chip" onclick="quickSend('ตารางเรียนวันนี้')">📅 ตารางเรียนวันนี้</div>
    <div class="chip" onclick="quickSend('บรีฟงานวันนี้')">📋 บรีฟงานวันนี้</div>
    <div class="chip" onclick="quickSend('สถานะระบบ')">💻 สถานะระบบ</div>
  </div>

  <div class="controls">
    <button class="icon-btn mic-btn" id="micBtn" onclick="toggleMic()">🎙️</button>
    <input type="text" id="queryInput" placeholder="พิมพ์คำสั่งหรือคุยกับ Javis..." onkeydown="if(event.key==='Enter') sendQuery()">
    <button class="icon-btn" onclick="sendQuery()">➤</button>
  </div>

  <div class="footer-note">Javis v0.3.1 • Powered by Gemini Flash & Jev Guardrail</div>

  <script>
    let token = localStorage.getItem("javis_token") || "TOKEN_PLACEHOLDER";
    if (token) localStorage.setItem("javis_token", token);

    function addMessage(text, sender) {
      const chat = document.getElementById("chat");
      const div = document.createElement("div");
      div.className = "msg " + sender;
      div.innerText = text;
      chat.appendChild(div);
      chat.scrollTop = chat.scrollHeight;
    }

    async function sendQuery(customText) {
      const input = document.getElementById("queryInput");
      const query = (customText || input.value).trim();
      if (!query) return;
      if (!customText) input.value = "";

      addMessage(query, "user");

      try {
        const res = await fetch("/v1/ask", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
          },
          body: JSON.stringify({ query: query })
        });
        const data = await res.json();
        if (data.reply) {
          addMessage(data.reply, "javis");
          // Play speech on iPhone using Web Speech Synthesis if available
          if ('speechSynthesis' in window) {
            const utter = new SpeechSynthesisUtterance(data.reply);
            utter.lang = 'th-TH';
            window.speechSynthesis.speak(utter);
          }
        } else if (data.error) {
          addMessage("⚠️ " + data.error, "javis");
        }
      } catch (err) {
        addMessage("❌ ไม่สามารถเชื่อมต่อกับ Javis OS ได้: " + err.message, "javis");
      }
    }

    function quickSend(text) {
      sendQuery(text);
    }

    // Voice Dictation (Safari iOS Web Speech API)
    let recognition = null;
    let isRecording = false;
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRec) {
      recognition = new SpeechRec();
      recognition.lang = "th-TH";
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onstart = () => {
        isRecording = true;
        document.getElementById("micBtn").classList.add("recording");
      };
      recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        if (transcript) sendQuery(transcript);
      };
      recognition.onerror = (e) => {
        console.error("Speech error", e);
        isRecording = false;
        document.getElementById("micBtn").classList.remove("recording");
      };
      recognition.onend = () => {
        isRecording = false;
        document.getElementById("micBtn").classList.remove("recording");
      };
    }

    function toggleMic() {
      if (!recognition) {
        alert("เบราว์เซอร์ไม่รองรับการแปลงเสียงเป็นข้อความ โปรดใช้การพิมพ์แทน หรือติดตั้ง Apple Shortcuts ครับ");
        return;
      }
      if (isRecording) {
        recognition.stop();
      } else {
        recognition.start();
      }
    }
  </script>
</body>
</html>
"""


class MobileCompanionServer:
    """Zero-dependency asyncio HTTP server exposing Web Companion and JSON API for iOS Shortcuts / Scriptable."""

    def __init__(self, orchestrator: Any, host: str = "0.0.0.0", port: int = 8765, token: Optional[str] = None) -> None:
        self.orchestrator = orchestrator
        self.host = host
        self.port = port
        self.token = token if token is not None else get_or_create_mobile_token()
        self._server: Optional[asyncio.AbstractServer] = None
        self._pending_confirms: Dict[str, dict] = {}

    async def process_request(self, method: str, path: str, headers: Dict[str, str], body: bytes) -> Tuple[int, Any]:
        """Core routing logic matching HTTP requests."""
        # 1. Health endpoint
        if path == "/v1/health" and method == "GET":
            return 200, {
                "status": "ok",
                "version": "0.3.1",
                "state": str(getattr(self.orchestrator, "state", "IDLE")),
                "guardrail": "Jev System One Active",
            }

        # 2. Web Companion UI for Safari on iPhone
        if path in ("/", "/index.html") and method == "GET":
            html = _MOBILE_HTML_PAGE.replace("TOKEN_PLACEHOLDER", self.token)
            return 200, html

        # 3. CORS Preflight
        if method == "OPTIONS":
            return 200, {"ok": True}

        # 4. Bearer Authentication for API endpoints
        auth = headers.get("authorization", "")
        if self.token and auth != f"Bearer {self.token}":
            return 401, {"error": "Unauthorized"}

        # 5. Core Ask Query
        if path == "/v1/ask" and method == "POST":
            try:
                payload = json.loads(body.decode("utf-8") or "{}")
            except Exception:
                payload = {}
            query = str(payload.get("query") or "").strip()
            want_tts = bool(payload.get("tts", False))
            if not query:
                return 400, {"error": "Missing query"}

            # Check if query requests a sensitive operation requiring mobile two-step confirmation
            sensitive_keywords = ["ลบไฟล์", "ลบโฟลเดอร์", "shutdown", "reboot", "ปิดเครื่อง", "รีสตาร์ท", "rm -", "delete"]
            is_sensitive = any(kw in query.lower() for kw in sensitive_keywords)
            if is_sensitive:
                confirm_id = secrets.token_hex(8)
                self._pending_confirms[confirm_id] = {
                    "query": query,
                    "ts": time.time(),
                }
                return 200, {
                    "reply": f"คำสั่งนี้อาจส่งผลต่อระบบ: \"{query}\" คุณต้องการยืนยันการดำเนินการหรือไม่?",
                    "requires_confirmation": True,
                    "confirm_id": confirm_id,
                    "state": str(getattr(self.orchestrator, "state", "IDLE")),
                }

            # Process query through Orchestrator pipeline
            if hasattr(self.orchestrator, "process_text_query"):
                reply = await self.orchestrator.process_text_query(query)
            elif hasattr(self.orchestrator, "llm") and hasattr(self.orchestrator.llm, "generate_response"):
                reply = await self.orchestrator.llm.generate_response(query)
            else:
                reply = "Javis พร้อมทำงานครับ"

            audio_b64 = None
            if want_tts and hasattr(self.orchestrator, "tts") and hasattr(self.orchestrator.tts, "synthesize_speech"):
                try:
                    mp3_bytes = await self.orchestrator.tts.synthesize_speech(reply)
                    if mp3_bytes:
                        audio_b64 = base64.b64encode(mp3_bytes).decode("ascii")
                except Exception as e:
                    logger.debug("TTS synthesis failed in mobile API: %s", e)

            resp_obj = {
                "reply": reply,
                "requires_confirmation": False,
                "state": str(getattr(self.orchestrator, "state", "IDLE")),
            }
            if audio_b64:
                resp_obj["audio_b64"] = audio_b64

            return 200, resp_obj

        # 6. Two-Step Confirmation Endpoint
        if path == "/v1/confirm" and method == "POST":
            try:
                payload = json.loads(body.decode("utf-8") or "{}")
            except Exception:
                payload = {}
            confirm_id = str(payload.get("confirm_id") or "").strip()
            approved = bool(payload.get("approved", False))

            if not confirm_id or confirm_id not in self._pending_confirms:
                return 404, {"error": "Invalid or expired confirm_id", "approved": False}

            pending = self._pending_confirms.pop(confirm_id)
            if not approved:
                return 200, {
                    "status": "cancelled",
                    "reply": "ยกเลิกคำสั่งเรียบร้อยครับ",
                    "approved": False,
                }

            query = pending["query"]
            if hasattr(self.orchestrator, "process_text_query"):
                reply = await self.orchestrator.process_text_query(query)
            elif hasattr(self.orchestrator, "llm") and hasattr(self.orchestrator.llm, "generate_response"):
                reply = await self.orchestrator.llm.generate_response(query)
            else:
                reply = "ดำเนินการเรียบร้อยครับ"

            return 200, {
                "status": "confirmed",
                "reply": f"ยืนยันและดำเนินการเรียบร้อยครับ: {reply}",
                "approved": True,
            }

        return 404, {"error": "Not found"}

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Low-level asyncio connection handler parsing HTTP/1.1 without third-party frameworks."""
        try:
            request_line = await reader.readline()
            if not request_line:
                return
            parts = request_line.decode("utf-8", errors="replace").strip().split(" ")
            if len(parts) < 2:
                return
            method, path = parts[0].upper(), parts[1]

            headers: Dict[str, str] = {}
            while True:
                line = await reader.readline()
                if not line or line in (b"\r\n", b"\n"):
                    break
                h_str = line.decode("utf-8", errors="replace").strip()
                if ":" in h_str:
                    k, v = h_str.split(":", 1)
                    headers[k.strip().lower()] = v.strip()

            content_length = int(headers.get("content-length", 0))
            body = b""
            if content_length > 0:
                body = await reader.readexactly(content_length)

            code, resp_data = await self.process_request(method, path, headers, body)

            if isinstance(resp_data, (dict, list)):
                resp_bytes = json.dumps(resp_data, ensure_ascii=False).encode("utf-8")
                content_type = "application/json; charset=utf-8"
            elif isinstance(resp_data, str):
                resp_bytes = resp_data.encode("utf-8")
                content_type = "text/html; charset=utf-8"
            else:
                resp_bytes = bytes(resp_data)
                content_type = "application/octet-stream"

            status_messages = {
                200: "OK",
                400: "Bad Request",
                401: "Unauthorized",
                404: "Not Found",
                500: "Internal Server Error",
            }
            status_text = status_messages.get(code, "OK")

            writer.write(f"HTTP/1.1 {code} {status_text}\r\n".encode())
            writer.write(f"Content-Type: {content_type}\r\n".encode())
            writer.write(f"Content-Length: {len(resp_bytes)}\r\n".encode())
            writer.write(b"Access-Control-Allow-Origin: *\r\n")
            writer.write(b"Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n")
            writer.write(b"Access-Control-Allow-Headers: Authorization, Content-Type\r\n")
            writer.write(b"Connection: close\r\n\r\n")
            writer.write(resp_bytes)
            await writer.drain()
        except Exception as e:
            logger.debug("[MobileCompanion] Connection error: %s", e)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self) -> None:
        """Starts the background asyncio TCP HTTP server."""
        if self._server is None:
            self._server = await asyncio.start_server(
                self._handle_connection,
                host=self.host,
                port=self.port,
            )
            logger.info("[MobileCompanion] Listening on http://%s:%d", self.host, self.port)

    async def stop(self) -> None:
        """Stops the server."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
