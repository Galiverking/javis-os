"""Tier 1.5: Opt-in Intent Router + Pre-Tool Security Guardrail.

Architecture (from Issue #2 / RFC):
  Tier 1 (Regex FastPath) ─► Tier 1.5 (this module, opt-in) ─► Tier 2 (Hermes / Gemini)

Responsibilities:
  1. Intent Routing: classify the user utterance into one of the known intent
     categories with low latency (~250 ms via lightweight heuristics + LLM
     verification when JEV_API_KEY is set).
  2. Pre-Tool Security Guardrail: reject requests that could be harmful or
     outside the allowed tool policy before they ever reach Hermes / Gemini's
     tool-call loop.

Opt-in activation:
  Set the env variable  JEV_API_KEY=<your-jev-or-any-llm-key>
  When unset: module runs in pure-heuristic mode (no external call, ~0 ms),
  which is still useful for the guardrail but skips LLM intent verification.

Zero RAM overhead: no models are loaded locally.
100% Free-stack compatible: Javis works identically without JEV_API_KEY.
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent taxonomy
# ---------------------------------------------------------------------------

INTENT_LABELS = [
    "query_time",
    "query_date",
    "query_battery",
    "query_system_status",
    "control_volume",
    "control_mute",
    "open_app",
    "open_website",
    "search_web",
    "life_manager",
    "study_timetable",
    "task_briefing",
    "general_question",   # → safe, forward to Hermes/Gemini
    "code_execution",     # → potentially risky, requires confirmation
    "file_operation",     # → potentially risky, requires confirmation
    "system_command",     # → potentially risky, requires confirmation
    "harmful_request",    # → blocked
    "unknown",
]

# ---------------------------------------------------------------------------
# Blocked patterns (pre-tool guardrail): run before forwarding to Tier 2
# ---------------------------------------------------------------------------

_BLOCKED_PATTERNS: List[re.Pattern] = [
    # rm -rf / dangerous shell commands
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
    re.compile(r"\bsudo\s+(rm|mkfs|dd\b|format)\b", re.IGNORECASE),
    # Exfiltration / data leak patterns
    re.compile(r"\b(curl|wget|nc|ncat)\b.*\|.*sh", re.IGNORECASE),
    re.compile(r"password|passwd\s+--?stdin", re.IGNORECASE),
    # Prompt injection attempts
    re.compile(r"ignore\s+(previous|all|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"(jailbreak|bypass|override)\s+(safety|filter|guardrail)", re.IGNORECASE),
    # Sensitive Thai language patterns
    re.compile(r"(ลบ|ฟอร์แมต|ทำลาย)\s*(ฮาร์ดดิสก์|ไดรฟ์|ดิสก์|ระบบ)", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Intent heuristic rules (fast, regex-based, ~0 ms)
# ---------------------------------------------------------------------------

_INTENT_HEURISTICS: List[Tuple[str, re.Pattern]] = [
    ("query_time",        re.compile(r"(กี่โมง|เวลาเท่าไหร่|ตอนนี้กี่โมง)")),
    ("query_date",        re.compile(r"(วันนี้วัน(อะไร|ที่)|วันที่เท่าไหร่)")),
    ("query_battery",     re.compile(r"(เช็คแบต|แบตเตอรี่|เหลือแบต)")),
    ("query_system_status", re.compile(r"(สถานะเครื่อง|RAM|CPU|ใช้แรม)")),
    ("control_volume",    re.compile(r"(เพิ่มเสียง|ลดเสียง|ปรับเสียง|volume)")),
    ("control_mute",      re.compile(r"(ปิดเสียง|เปิดเสียง|mute|unmute)")),
    ("study_timetable",   re.compile(r"(ตารางเรียน|เรียนอะไรบ้าง|วันนี้มีเรียน)")),
    # life_manager MUST come before open_app to prevent "เปิด Life Manager" matching open_app
    ("life_manager",      re.compile(r"(life\s*manager|จัดการชีวิต|การบ้าน|ภารกิจ)", re.IGNORECASE)),
    ("task_briefing",     re.compile(r"(สรุปงาน|บรีฟงาน|งานค้าง)")),
    ("open_website",      re.compile(r"เปิด\s*(เว็บ)?\s*(youtube|google|github|facebook|ยูทูป|กูเกิล)")),
    ("search_web",        re.compile(r"(ค้นหา|เสิร์ช|หาข้อมูล)")),
    ("open_app",          re.compile(r"^เปิด\s+(แอป|โปรแกรม)?[a-zA-Z0-9ก-๙]", re.IGNORECASE)),
    ("code_execution",    re.compile(r"(รันโค้ด|execute|eval\(|exec\(|python -c)", re.IGNORECASE)),
    ("file_operation",    re.compile(r"(ลบไฟล์|เปลี่ยนชื่อไฟล์|คัดลอกไฟล์|ย้ายไฟล์|rm |mv |cp )")),
    ("system_command",    re.compile(r"(sudo|shutdown|reboot|systemctl|service\s)", re.IGNORECASE)),
]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class GuardrailDecision:
    """Result from Tier 1.5 evaluation."""
    allowed: bool
    intent: str = "unknown"
    confidence: float = 0.0
    block_reason: Optional[str] = None
    # Whether Tier 1.5 is running in heuristic-only mode (no JEV key)
    heuristic_only: bool = True
    # Time taken for this evaluation, milliseconds
    latency_ms: float = 0.0
    # True  → forward to Tier 2 Hermes/Gemini
    # False → Tier 1 already handles it, or it is blocked
    forward_to_tier2: bool = True


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class Tier15Guardrail:
    """Opt-in Tier 1.5 Guardrail + Intent Router for Javis OS.

    Usage:
        guardrail = Tier15Guardrail()       # reads JEV_API_KEY from env
        decision = guardrail.evaluate(text)
        if not decision.allowed:
            # blocked → reject request
        else:
            # use decision.intent and decision.forward_to_tier2
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("JEV_API_KEY")
        self._heuristic_only = not bool(self.api_key)
        if self._heuristic_only:
            logger.debug(
                "[Tier 1.5] No JEV_API_KEY set → running in heuristic-only mode (no latency overhead)."
            )
        else:
            logger.info("[Tier 1.5] JEV_API_KEY found → LLM-assisted intent verification enabled.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(self, text: str) -> GuardrailDecision:
        """Evaluate a user utterance synchronously (no async required).

        Returns a GuardrailDecision within ~0–300 ms depending on mode.
        """
        t0 = time.perf_counter()

        # Step 1: Blocked-pattern scan (always, ~0 ms)
        block_reason = self._check_blocked(text)
        if block_reason:
            latency = (time.perf_counter() - t0) * 1000
            logger.warning("[Tier 1.5] BLOCKED(%s): %.0f ms | %.40s", block_reason, latency, text)
            return GuardrailDecision(
                allowed=False,
                intent="harmful_request",
                confidence=1.0,
                block_reason=block_reason,
                heuristic_only=self._heuristic_only,
                latency_ms=latency,
                forward_to_tier2=False,
            )

        # Step 2: Heuristic intent detection (~0 ms)
        intent, confidence = self._heuristic_intent(text)

        # Step 3: (Opt-in) LLM verification for risky or unknown intents
        if not self._heuristic_only and intent in ("unknown", "code_execution", "file_operation", "system_command"):
            intent, confidence = self._llm_verify_intent(text, intent)

        # Step 4: Policy enforcement on detected intent
        if intent in ("harmful_request",):
            block_reason = f"Policy: intent={intent}"
            latency = (time.perf_counter() - t0) * 1000
            logger.warning("[Tier 1.5] BLOCKED(%s): %.0f ms", block_reason, latency)
            return GuardrailDecision(
                allowed=False,
                intent=intent,
                confidence=confidence,
                block_reason=block_reason,
                heuristic_only=self._heuristic_only,
                latency_ms=latency,
                forward_to_tier2=False,
            )

        # Determine if Tier 1 handles it (no need to escalate)
        tier1_intents = {
            "query_time", "query_date", "query_battery", "query_system_status",
            "control_volume", "control_mute", "open_app", "open_website",
            "search_web", "life_manager", "study_timetable", "task_briefing",
        }
        forward = intent not in tier1_intents

        latency = (time.perf_counter() - t0) * 1000
        logger.debug(
            "[Tier 1.5] intent=%s conf=%.2f fwd=%s heuristic=%s %.0f ms",
            intent, confidence, forward, self._heuristic_only, latency,
        )
        return GuardrailDecision(
            allowed=True,
            intent=intent,
            confidence=confidence,
            heuristic_only=self._heuristic_only,
            latency_ms=latency,
            forward_to_tier2=forward,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_blocked(self, text: str) -> Optional[str]:
        """Return a human-readable block reason if any blocked pattern matches, else None."""
        for pattern in _BLOCKED_PATTERNS:
            if pattern.search(text):
                return pattern.pattern
        return None

    def _heuristic_intent(self, text: str) -> Tuple[str, float]:
        """Fast regex-based intent detection.  Returns (intent_label, confidence)."""
        clean = text.strip()
        for intent_label, pattern in _INTENT_HEURISTICS:
            if pattern.search(clean):
                return intent_label, 0.85
        return "general_question", 0.5

    def _llm_verify_intent(self, text: str, heuristic_intent: str) -> Tuple[str, float]:
        """Call lightweight LLM (via JEV_API_KEY / Gemini Flash-lite) for verification.
        Falls back to heuristic result on any error.
        """
        try:
            import httpx  # already a project dependency

            system_prompt = (
                "You are an intent classifier for a Thai voice assistant. "
                "Classify the user message into ONE of these labels: "
                + ", ".join(INTENT_LABELS)
                + ". Reply with ONLY the label, nothing else."
            )
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": f"{system_prompt}\n\nUser: {text}"}]}
                ],
                "generationConfig": {"maxOutputTokens": 20, "temperature": 0.0},
            }
            # Reuse Gemini Flash-Lite endpoint (JEV_API_KEY treated as GEMINI_API_KEY fallback)
            api_key = self.api_key
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-2.0-flash-lite:generateContent?key={api_key}"
            )
            with httpx.Client(timeout=2.5) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    label = (
                        res.json()
                        .get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", heuristic_intent)
                        .strip()
                        .lower()
                    )
                    if label in INTENT_LABELS:
                        return label, 0.95
        except Exception as exc:
            logger.debug("[Tier 1.5] LLM verify failed (%s), using heuristic fallback.", exc)
        return heuristic_intent, 0.6
