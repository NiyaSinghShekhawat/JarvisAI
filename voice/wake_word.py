"""Backward-compatible wake imports.

The implementation now lives in voice.wake. Existing Jarvis imports continue
working without changing the rest of the application.
"""
from voice.wake.listener import WakeListener
from voice.wake.stop_word_detector import StopWordWorker

WakeWordWorker = WakeListener

__all__ = ["WakeWordWorker", "StopWordWorker"]
