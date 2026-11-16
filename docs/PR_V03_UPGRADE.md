# Javis OS v0.3.0 Upgrade Summary

## Key Enhancements

1. **Zero-Weight Numpy RMS VAD Auto-Endpointing**
   - Lightweight Voice Activity Detection using Numpy RMS energy calculation for automatic speech endpointing without heavy ML dependencies.

2. **Zero-Disk In-Memory WAV -> Groq Whisper**
   - Direct in-memory WAV encoding and streaming to Groq Whisper API, eliminating temporary disk I/O latency.

3. **3-Tier Brain Routing**
   - `FastPathRouter` -> `HermesGatewayClient` (port 8000) -> `Gemini 2.5 Flash Tool Loop` for optimal latency and capability fallback.

4. **2-Tier ToolPolicyEngine + Zenity Confirmation**
   - Enforces safe tool execution with a two-tier policy engine and interactive Zenity GUI confirmation prompts for sensitive actions.

5. **Unified `wpctl`/`pactl` Volume Control**
   - Seamless system audio volume management supporting both PipeWire (`wpctl`) and PulseAudio (`pactl`).

6. **Sentence-Chunked Streaming EdgeTTS + LRU RAM Cache**
   - Low-latency text-to-speech playback via sentence-level chunked streaming with EdgeTTS and an in-memory LRU cache.

7. **SQLite MemoryStore & CLI Commands**
   - Persistent conversational/system memory backed by SQLite (`MemoryStore`), plus new CLI commands: `ask`, `tools`, and `calibrate`.

## Test Results
- **17/17 tests passed**
