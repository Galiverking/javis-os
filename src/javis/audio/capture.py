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
        """Detect best input device. Prioritize ALSA Loopback hw:1,1 (WO Mic / iPhone) if active."""
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            name = dev.get("name", "")
            if dev.get("max_input_channels", 0) > 0:
                if "Loopback" in name and "hw:1,1" in name:
                    return idx, 48000, 3  # downsample factor = 3 (48000 -> 16000)
        
        # Fallback to system default input device
        def_dev = sd.default.device[0] if sd.default.device[0] is not None else None
        return def_dev, self.sample_rate, 1

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
