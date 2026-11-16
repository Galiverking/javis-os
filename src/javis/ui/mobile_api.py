"""Lightweight Asyncio HTTP Mobile Companion Bridge for iPhone (Apple Shortcuts + Scriptable Widget)."""
import asyncio
import json
import os
import secrets
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


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


class MobileCompanionServer:
    """Zero-dependency asyncio HTTP server exposing /v1/health and /v1/ask for iOS Shortcuts & Scriptable."""

    def __init__(self, orchestrator: Any, host: str = "0.0.0.0", port: int = 8765, token: Optional[str] = None) -> None:
        self.orchestrator = orchestrator
        self.host = host
        self.port = port
        self.token = token if token is not None else get_or_create_mobile_token()
        self._server: Optional[asyncio.AbstractServer] = None

    async def process_request(self, method: str, path: str, headers: Dict[str, str], body: bytes) -> Tuple[int, Dict[str, Any]]:
        if path == "/v1/health" and method == "GET":
            return 200, {"status": "ok", "version": "0.3.1", "state": str(getattr(self.orchestrator, "state", "IDLE"))}
        auth = headers.get("authorization", "")
        if self.token and auth != f"Bearer {self.token}":
            return 401, {"error": "Unauthorized"}
        if path == "/v1/ask" and method == "POST":
            payload = json.loads(body.decode("utf-8") or "{}")
            query = str(payload.get("query") or "").strip()
            if not query:
                return 400, {"error": "Missing query"}
            reply = await self.orchestrator.llm.generate_response(query)
            return 200, {"reply": reply, "state": str(getattr(self.orchestrator, "state", "IDLE"))}
        return 404, {"error": "Not found"}
