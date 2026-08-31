"""Shared microphone configuration for the Jarvis voice pipeline."""

# Explicitly use the Intel microphone through Windows WASAPI.
MIC_DEVICE = 9
MIC_SAMPLE_RATE = 48000
MIC_CHANNELS = 1

# openWakeWord expects 16 kHz audio.
WAKE_SAMPLE_RATE = 16000

# The active microphone is known to produce a healthy signal on channel 0.
MIC_CHANNEL = 0
