"""Edge-TTS Integration for Javis OS.
Uses Microsoft Edge Online Speech API (100% Free).
Default Voice: th-TH-PremwadeeNeural (selected by user).
Features Thai Sentence Chunker with min-buffer rule (35 chars) to prevent stutter.
"""

import asyncio
import io
import re
from typing import AsyncIterator, List


DEFAULT_VOICE = "th-TH-NiwatNeural"
MIN_CHUNK_CHARS = 35


class ThaiSentenceChunker:
    """Chunks Thai streaming LLM tokens into natural spoken sentences.
    Prevents stuttering and rate limits by enforcing a minimum buffer size.
    """

    def __init__(self, min_chars: int = MIN_CHUNK_CHARS) -> None:
        self.min_chars = min_chars
        self.buffer = ""

    def feed(self, token: str) -> List[str]:
        """Feed token from streaming LLM and return completed sentence chunks if ready."""
        self.buffer += token
        chunks = []

        while len(self.buffer) >= self.min_chars:
            # 1. Look for newline first
            if "\n" in self.buffer:
                idx = self.buffer.index("\n")
                chunk = self.buffer[:idx].strip()
                self.buffer = self.buffer[idx + 1:]
                if chunk:
                    chunks.append(chunk)
                continue

            # 2. Look for punctuation (. ! ? ,) after min_chars
            match = re.search(r"([.!?,])", self.buffer[self.min_chars:])
            if match:
                cut_idx = self.min_chars + match.end()
                chunk = self.buffer[:cut_idx].strip()
                self.buffer = self.buffer[cut_idx:]
                if chunk:
                    chunks.append(chunk)
                continue

            # 3. Look for whitespace / conjunction boundary after min_chars
            ws_match = re.search(r"(\s+|(?:แล้ว|และ|หรือ|เพราะว่า|แต่))", self.buffer[self.min_chars:])
            if ws_match:
                cut_idx = self.min_chars + ws_match.start()
                chunk = self.buffer[:cut_idx].strip()
                self.buffer = self.buffer[cut_idx:]
                if chunk:
                    chunks.append(chunk)
                continue

            # If no boundary found yet, wait for more tokens unless buffer is overly long (> 120 chars)
            if len(self.buffer) > 120:
                chunks.append(self.buffer.strip())
                self.buffer = ""
            break

        return chunks

    def flush(self) -> List[str]:
        """Flush remaining buffer at end of generation."""
        remainder = self.buffer.strip()
        self.buffer = ""
        return [remainder] if remainder else []


class EdgeTTSClient:
    """Synthesizes Thai speech via edge-tts."""

    def __init__(self, voice: str = DEFAULT_VOICE) -> None:
        self.voice = voice

    async def synthesize_stream(self, text: str) -> bytes:
        """Synthesize text to MP3 audio bytes using edge-tts with automatic fallback."""
        import edge_tts

        voices_to_try = [self.voice]
        if self.voice != DEFAULT_VOICE:
            voices_to_try.append(DEFAULT_VOICE)

        for v in voices_to_try:
            try:
                communicate = edge_tts.Communicate(text, v)
                audio_stream = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_stream.write(chunk["data"])
                data = audio_stream.getvalue()
                if data:
                    return data
            except Exception as e:
                pass
        return b""

    async def synthesize_speech(self, text: str) -> bytes:
        """Alias for synthesize_stream."""
        return await self.synthesize_stream(text)
