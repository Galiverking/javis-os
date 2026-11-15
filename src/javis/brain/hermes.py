"""Hermes Gateway Connector for Javis OS.
Connects to Hermes Gateway running at http://localhost:8000.
Implements Soft Timeout (3.5s) and Circuit Breaker to fall back to Direct Free Provider if Hermes is busy/offline.
"""

import asyncio
import time
from typing import AsyncIterator, Optional
import httpx


DEFAULT_HERMES_URL = "http://localhost:8000"
SOFT_TIMEOUT_SECONDS = 3.5


class HermesGatewayClient:
    """Client for querying Hermes Agent Gateway with resilience."""

    def __init__(self, base_url: str = DEFAULT_HERMES_URL, timeout: float = SOFT_TIMEOUT_SECONDS) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.circuit_open = False
        self._last_failure_time = 0.0
        self._cooldown_seconds = 15.0

    async def check_health(self) -> bool:
        """Check if Hermes Gateway is alive and responsive."""
        # If circuit is open, check if cooldown elapsed
        if self.circuit_open and (time.monotonic() - self._last_failure_time) < self._cooldown_seconds:
            return False

        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                res = await client.get(f"{self.base_url}/")
                is_alive = res.status_code < 500
                if is_alive:
                    self.circuit_open = False
                return is_alive
        except Exception:
            self.circuit_open = True
            self._last_failure_time = time.monotonic()
            return False

    async def ask(self, query: str) -> Optional[str]:
        """Send user query to Hermes Gateway.
        Returns response string if successful, or None if timed out / circuit broken (triggering fallback).
        """
        if self.circuit_open and (time.monotonic() - self._last_failure_time) < self._cooldown_seconds:
            return None  # Fast fail to trigger fallback immediately

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "prompt": query,
                    "max_tokens": 200,
                    "temperature": 0.5,
                }
                # Try standard completions endpoint
                res = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                return None
        except (httpx.TimeoutException, httpx.ConnectError):
            self.circuit_open = True
            self._last_failure_time = time.monotonic()
            return None
