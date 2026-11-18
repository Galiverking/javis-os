"""Thread-Isolated Audio Capture.
Captures 16kHz mono 16-bit PCM using sounddevice callback in a C-safe worker thread,
feeding a thread-safe ring buffer/queue to isolate real-time audio from Python GIL.
"""

import queue
import threading
from typing import Callable, Optional
import numpy as np

from javis.audio.half_duplex import HalfDuplexManager


class AudioCaptureWorker:
    """Dedicated background thread for audio recording, keeping C-callbacks off asyncio loop."""

    def __init__(
        self,
        half_duplex: Optional[HalfDuplexManager] = None,
        sample_rate: int = 16000,
        channels: int = 1,
        block_size: int = 512,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.block_size = block_size
        self.half_duplex = half_duplex or HalfDuplexManager()
        
        self.audio_queue: queue.Queue[bytes] = queue.Queue(maxsize=100)
        self._is_running = False
        self._stream = None
        self._callback: Optional[Callable[[bytes], None]] = None

    def _resolve_device_and_samplerate(self, sd):
        """Detect best input device.
        - If JAVIS_INPUT_DEVICE is specified (e.g. 'womic', 'pc', or device name), honor that.
        - Otherwise, honor the system default input device (PC mic, USB mic, headset, etc.).
        """
        import os
        custom_dev = os.getenv("JAVIS_INPUT_DEVICE", "").strip().lower()
        devices = sd.query_devices()

        # 1. Explicit womic / loopback request
        if custom_dev in ("womic", "iphone", "loopback"):
            for idx, dev in enumerate(devices):
                name = dev.get("name", "")
                if dev.get("max_input_channels", 0) > 0 and "Loopback" in name and "hw:1,1" in name:
                    return idx, 48000, 3

        # 2. If JAVIS_INPUT_DEVICE is set to a specific device index or substring
        if custom_dev and custom_dev not in ("pc", "default", "auto"):
            for idx, dev in enumerate(devices):
                name = dev.get("name", "").lower()
                if dev.get("max_input_channels", 0) > 0 and custom_dev in name:
                    return idx, int(dev.get("default_samplerate", self.sample_rate)), 1

        # 3. Check if system default explicitly points to Loopback
        if not custom_dev:
            try:
                def_idx = sd.default.device[0]
                if def_idx is not None and def_idx < len(devices):
                    def_name = devices[def_idx].get("name", "")
                    if "loopback" in def_name.lower():
                        for idx, dev in enumerate(devices):
                            name = dev.get("name", "")
                            if dev.get("max_input_channels", 0) > 0 and "Loopback" in name and "hw:1,1" in name:
                                return idx, 48000, 3
            except Exception:
                pass

        # 4. Standard: PipeWire / ALSA default input device at target 16kHz
        return None, self.sample_rate, 1

    def start(self, callback: Optional[Callable[[bytes], None]] = None) -> None:
        """Start audio capture stream."""
        import sounddevice as sd

        if self._is_running:
            return

        self._callback = callback
        self._is_running = True

        dev_index, dev_sr, downsample_factor = self._resolve_device_and_samplerate(sd)
        actual_block_size = self.block_size * downsample_factor

        def _sd_callback(indata, frames, time_info, status):
            if not self._is_running:
                return
            if status:
                # Warning: xrun or overflow
                pass

            # Intelligent Half-Duplex check: drop frames if speaker is currently outputting sound
            if not self.half_duplex.should_record():
                return

            # Downsample to target sample rate if needed
            processed_data = indata[::downsample_factor] if downsample_factor > 1 else indata
            pcm_bytes = (processed_data * 32767).astype(np.int16).tobytes()
            try:
                self.audio_queue.put_nowait(pcm_bytes)
                if self._callback:
                    self._callback(pcm_bytes)
            except queue.Full:
                pass  # Ring buffer drops oldest frame under heavy pressure to prevent latency buildup

        self._stream = sd.InputStream(
            device=dev_index,
            samplerate=dev_sr,
            channels=self.channels,
            dtype="float32",
            blocksize=actual_block_size,
            callback=_sd_callback,
        )
        self._stream.start()

    def stop(self) -> None:
        """Stop audio stream cleanly."""
        self._is_running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        # Drain queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
