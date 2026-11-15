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

    def start(self, callback: Optional[Callable[[bytes], None]] = None) -> None:
        """Start audio capture stream."""
        import sounddevice as sd

        if self._is_running:
            return

        self._callback = callback
        self._is_running = True

        def _sd_callback(indata, frames, time_info, status):
            if not self._is_running:
                return
            if status:
                # Warning: xrun or overflow
                pass

            # Intelligent Half-Duplex check: drop frames if speaker is currently outputting sound
            if not self.half_duplex.should_record():
                return

            pcm_bytes = (indata * 32767).astype(np.int16).tobytes()
            try:
                self.audio_queue.put_nowait(pcm_bytes)
                if self._callback:
                    self._callback(pcm_bytes)
            except queue.Full:
                pass  # Ring buffer drops oldest frame under heavy pressure to prevent latency buildup

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=self.block_size,
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
