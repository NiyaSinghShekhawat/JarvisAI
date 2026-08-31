"""Compatibility facade for the unified wake subsystem.

Application code should prefer ``from voice.wake import WakeListener`` and
``from voice.wake import StopWordWorker``. This module remains temporarily so
older imports cannot accidentally instantiate a second wake implementation.
"""

from voice.wake import StopWordWorker, WakeListener

WakeWordWorker = WakeListener

__all__ = ["WakeWordWorker", "StopWordWorker"]
