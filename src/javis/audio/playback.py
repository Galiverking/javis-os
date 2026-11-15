"""Audio Playback Engine.
Handles PCM/WAV playback via sounddevice and coordinates with HalfDuplexManager.
Supports instant interruption (cancel).
"""

import threading
from typing import Optional
import numpy as np

from javis.audio.half_duplex import HalfDuplexManager


class AudioPlaybackEngine:
    """Manages audio playback and signals half-duplex state."""

    def __init__(self, half_duplex: Optional[HalfDuplexManager] = None) -> None:
        self.half_duplex = half_duplex or HalfDuplexManager()
        self._current_stream = None
        self._lock = threading.Lock()

    def play_pcm(self, pcm_data: bytes, sample_rate: int = 24000) -> None:
        """Play raw 16-bit PCM synchronously in caller thread or helper."""
        import sounddevice as sd

        self.half_duplex.playback_started()
        try:
            audio_array = np.frombuffer(pcm_data, dtype=np.int16)
            sd.play(audio_array, samplerate=sample_rate)
            sd.wait()
        finally:
            self.half_duplex.playback_stopped()

    def play_mp3(self, mp3_data: bytes, sample_rate: int = 24000) -> None:
        """Convert MP3 bytes to PCM via ffmpeg and play."""
        import subprocess

        self.half_duplex.playback_started()
        try:
            cmd = ["ffmpeg", "-loglevel", "quiet", "-i", "pipe:0", "-f", "s16le", "-ar", str(sample_rate), "-ac", "1", "pipe:1"]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            pcm_out, _ = proc.communicate(input=mp3_data)
            if pcm_out:
                import sounddevice as sd
                audio_array = np.frombuffer(pcm_out, dtype=np.int16)
                sd.play(audio_array, samplerate=sample_rate)
                sd.wait()
        finally:
            self.half_duplex.playback_stopped()

    def stop(self) -> None:
        """Instant interrupt / cancel playback."""
        import sounddevice as sd

        sd.stop()
        self.half_duplex.playback_stopped()
