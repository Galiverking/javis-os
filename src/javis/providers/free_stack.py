"""100% Free-Tier AI Provider Adapters for Javis OS.
Follows PersonalAIBot-ESP32 architecture:
- Free STT: Groq Whisper-large-v3-turbo (Free Tier)
- Free LLM: Google Gemini 1.5/2.0 Flash / Flash-Lite (Google AI Studio Free Tier: 15 RPM, 1M TPM)
- Fallback: Local rule-based responses if offline or keys missing.
"""

import os
from typing import Optional
import httpx


class FreeTierLLMClient:
    """Google Gemini AI Studio Free-Tier Client with automatic model fallback & Groq backup."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash-lite") -> None:
        self.api_key = api_key if api_key is not None else (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.model = model

    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call Gemini Free Tier API with multi-tier fallback."""
        if not self.api_key and not self.groq_api_key:
            return "ขณะนี้ยังไม่ได้ตั้งค่า API Key ขออภัยครับ กรุณาตั้งค่า GEMINI_API_KEY หรือต่อเน็ตนะครับ"

        # 1. Try Gemini Flash models
        if self.api_key:
            candidate_models = [self.model, "gemini-2.5-flash", "gemini-2.5-flash-lite"]
            seen_models = set()
            for m in candidate_models:
                if m in seen_models:
                    continue
                seen_models.add(m)

                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={self.api_key}"
                contents = []
                if system_prompt:
                    contents.append({"role": "user", "parts": [{"text": f"Instruction: {system_prompt}"}]})
                    contents.append({"role": "model", "parts": [{"text": "รับทราบครับ"}]})
                contents.append({"role": "user", "parts": [{"text": prompt}]})

                payload = {
                    "contents": contents,
                    "generationConfig": {
                        "maxOutputTokens": 1024,
                        "temperature": 0.6,
                    }
                }

                try:
                    async with httpx.AsyncClient(timeout=8.0) as client:
                        res = await client.post(url, json=payload)
                        if res.status_code == 200:
                            data = res.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                if parts:
                                    return parts[0].get("text", "").strip()
                        elif res.status_code == 429:
                            continue  # Quota limit on this model, try next model
                except Exception:
                    continue

        # 2. Fallback to Groq Qwen if Gemini is 429 or unavailable
        if self.groq_api_key:
            try:
                groq_url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {self.groq_api_key}", "Content-Type": "application/json"}
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                payload = {
                    "model": "qwen/qwen3.8-27b",
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.6,
                }
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.post(groq_url, headers=headers, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        choices = data.get("choices", [])
                        if choices:
                            text = choices[0].get("message", {}).get("content", "").strip()
                            if text:
                                return text
            except Exception as e:
                print(f"⚠️ [Groq Fallback Exception] {e}")

        return "ขออภัยครับ ไม่สามารถติดต่อระบบประมวลผลสมองภายนอกได้ในขณะนี้ครับ"


class FreeTierSTTClient:
    """Groq Free-Tier Whisper Client for Thai STT."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("GROQ_API_KEY")

    async def transcribe(self, wav_bytes: bytes, filename: str = "audio.wav") -> Optional[str]:
        """Transcribe Thai audio to text using Groq Cloud Free Tier."""
        if not self.api_key:
            return None

        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {"file": (filename, wav_bytes, "audio/wav")}
        data = {
            "model": "whisper-large-v3-turbo",
            "language": "th",
            "response_format": "json",
            "temperature": "0.0",
        }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                res = await client.post(url, headers=headers, files=files, data=data)
                if res.status_code == 200:
                    return res.json().get("text", "").strip()
                print(f"⚠️ [Groq STT Error] {res.status_code}: {res.text}")
                return None
        except Exception as e:
            print(f"⚠️ [Groq STT Exception] {type(e).__name__}: {e}")
            return None
