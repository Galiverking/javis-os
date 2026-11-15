import numpy as np
from javis.audio.chime import _generate_tone
from javis.core.daemon import VoicePipelineOrchestrator, VoiceState


def test_generate_tone():
    tone = _generate_tone(440.0, 0.05, sample_rate=16000, volume=0.2)
    assert isinstance(tone, np.ndarray)
    assert len(tone) == int(16000 * 0.05)
    assert tone.dtype == np.int16


def test_orchestrator_initial_state():
    orch = VoicePipelineOrchestrator()
    assert orch.state == VoiceState.IDLE
    assert len(orch._audio_buffer) == 0


def test_orchestrator_pcm_to_wav():
    orch = VoicePipelineOrchestrator()
    dummy_pcm = b"\x00\x00" * 1600  # 0.1 sec of silence at 16kHz 16-bit
    wav_bytes = orch._pcm_to_wav(dummy_pcm, sample_rate=16000)
    assert len(wav_bytes) > len(dummy_pcm)
    assert wav_bytes[:4] == b"RIFF"
    assert wav_bytes[8:12] == b"WAVE"
