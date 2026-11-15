"""Audio UX Chimes & Audio Cues.
Generates pure sine-wave chimes with smooth envelope to give instant, zero-latency feedback
when PTT triggers or status changes occur.
"""

import numpy as np
import sounddevice as sd


def _generate_tone(freq: float, duration: float, sample_rate: int = 16000, volume: float = 0.3) -> np.ndarray:
    """Generate a pure tone with smooth cosine fade-in and fade-out to prevent clicks."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    waveform = np.sin(2 * np.pi * freq * t) * volume
    
    # Apply fade-in and fade-out (first/last 10ms)
    fade_len = int(sample_rate * 0.01)
    if len(waveform) > 2 * fade_len:
        fade_in = (1 - np.cos(np.linspace(0, np.pi, fade_len))) / 2
        fade_out = (1 + np.cos(np.linspace(0, np.pi, fade_len))) / 2
        waveform[:fade_len] *= fade_in
        waveform[-fade_len:] *= fade_out
        
    return (waveform * 32767).astype(np.int16)


def play_start_chime(sample_rate: int = 16000) -> None:
    """Crisp high-pitch ascending chime (880Hz -> 1175Hz) indicating microphone is listening."""
    t1 = _generate_tone(880.0, 0.05, sample_rate=sample_rate, volume=0.25)
    t2 = _generate_tone(1174.66, 0.07, sample_rate=sample_rate, volume=0.25)
    combined = np.concatenate([t1, t2])
    sd.play(combined, samplerate=sample_rate)
    sd.wait()


def play_stop_chime(sample_rate: int = 16000) -> None:
    """Warm descending chime (880Hz -> 587Hz) indicating processing has started."""
    t1 = _generate_tone(880.0, 0.04, sample_rate=sample_rate, volume=0.2)
    t2 = _generate_tone(587.33, 0.06, sample_rate=sample_rate, volume=0.2)
    combined = np.concatenate([t1, t2])
    sd.play(combined, samplerate=sample_rate)
    sd.wait()


def play_error_chime(sample_rate: int = 16000) -> None:
    """Low alert tone for errors or no speech detected."""
    t1 = _generate_tone(330.0, 0.08, sample_rate=sample_rate, volume=0.3)
    sd.play(t1, samplerate=sample_rate)
    sd.wait()
