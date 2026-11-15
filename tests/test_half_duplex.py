"""Tests for Intelligent Half-Duplex audio coordinator."""

import pytest
from javis.audio.half_duplex import HalfDuplexManager


def test_half_duplex_state_transitions():
    manager = HalfDuplexManager(cadence_gap_ms=100)

    # Initial state: Should allow recording
    assert manager.should_record() is True
    assert manager.is_playing is False

    # When playback starts: Mic input must be muted to avoid echo loop
    manager.playback_started()
    assert manager.is_playing is True
    assert manager.should_record() is False

    # Force full duplex (e.g. headset plugged in)
    manager.set_force_full_duplex(True)
    assert manager.should_record() is True

    # Turn off full duplex, stop playback
    manager.set_force_full_duplex(False)
    manager.playback_stopped()
    assert manager.is_playing is False
