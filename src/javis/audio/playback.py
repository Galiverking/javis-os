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
        self._current_proc = None
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
        """Convert MP3 and play via PipeWire native pw-play (or mpv / sounddevice fallback)."""
        import shutil
        import subprocess

        self.half_duplex.playback_started()
        try:
            # 1. Prefer native pw-play on PipeWire systems for zero buffer underrun
            if shutil.which("pw-play") and shutil.which("ffmpeg"):
                try:
                    p_ffmpeg = subprocess.Popen(
                        ["ffmpeg", "-loglevel", "quiet", "-i", "pipe:0", "-f", "wav", "pipe:1"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                    )
                    p_play = subprocess.Popen(
                        ["pw-play", "-"],
                        stdin=p_ffmpeg.stdout,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    with self._lock:
                        self._current_proc = p_play
                    p_ffmpeg.stdin.write(mp3_data)
                    p_ffmpeg.stdin.close()
                    p_play.wait()
                    return
                except Exception:
                    pass

            # 2. Fallback to sounddevice
            cmd = ["ffmpeg", "-loglevel", "quiet", "-i", "pipe:0", "-f", "s16le", "-ar", str(sample_rate), "-ac", "1", "pipe:1"]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            pcm_out, _ = proc.communicate(input=mp3_data)
            if pcm_out:
                import sounddevice as sd
                audio_array = np.frombuffer(pcm_out, dtype=np.int16)
                sd.play(audio_array, samplerate=sample_rate)
                sd.wait()
        finally:
            with self._lock:
                self._current_proc = None
            self.half_duplex.playback_stopped()

    def stop(self) -> None:
        """Instant interrupt / cancel playback."""
        import sounddevice as sd

        with self._lock:
            if self._current_proc:
                try:
                    self._current_proc.terminate()
                except Exception:
                    pass
                self._current_proc = None

        sd.stop()
        self.half_duplex.playback_stopped()
