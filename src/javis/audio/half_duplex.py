"""Half-Duplex Audio Coordinator.
Prevents acoustic feedback / echo loop on laptop built-in mic/speakers
by suppressing mic frame ingestion while playback is active.
"""

import threading
import time
from typing import Optional


class HalfDuplexManager:
    """Coordinates recording and playback to avoid acoustic echo feedback."""

    def __init__(self, cadence_gap_ms: int = 350) -> None:
        self.cadence_gap_ms = cadence_gap_ms
        self._playback_lock = threading.Lock()
        self._is_playing = False
        self._force_full_duplex = False
        self._last_playback_stop_time = 0.0

    @property
    def is_playing(self) -> bool:
        with self._playback_lock:
            return self._is_playing

    def set_force_full_duplex(self, enabled: bool) -> None:
        """Allow full-duplex barge-in only if headset is connected or PipeWire AEC is enabled."""
        with self._playback_lock:
            self._force_full_duplex = enabled

    def playback_started(self) -> None:
        """Called by playback engine when audio synthesis output begins."""
        with self._playback_lock:
            self._is_playing = True

    def playback_stopped(self) -> None:
        """Called when playback finishes or is canceled."""
        with self._playback_lock:
            self._is_playing = False
            self._last_playback_stop_time = time.monotonic()

    def should_record(self) -> bool:
        """Returns True if mic audio frames should be processed, False if muted/dropped."""
        with self._playback_lock:
            if self._force_full_duplex:
                return True
            if self._is_playing:
                return False
            # Check cadence debounce window after playback stopped (avoid trailing echo)
            elapsed_ms = (time.monotonic() - self._last_playback_stop_time) * 1000.0
            return elapsed_ms >= 100.0
