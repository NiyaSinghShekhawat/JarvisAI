import time
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
import speech_recognition as sr
from scipy.signal import resample_poly

from voice.audio_config import MIC_CHANNELS, MIC_DEVICE, MIC_SAMPLE_RATE, WAKE_SAMPLE_RATE


class SpeechToText:
    """Microphone capture + speech recognition using Jarvis's shared mic."""

    def __init__(
        self,
        sample_rate: int = MIC_SAMPLE_RATE,
        channels: int = MIC_CHANNELS,
        silence_threshold: float = 0.015,
        silence_duration: float = 0.8,
        max_duration: float = 15.0,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.max_duration = max_duration
        self.recognizer = sr.Recognizer()

    def record_until_silence(
        self,
        level_callback: Optional[Callable[[float], None]] = None,
    ):
        frames: list[np.ndarray] = []
        silence_start: Optional[float] = None
        has_spoken = False
        start_time = time.time()

        def callback(indata, frame_count, time_info, status):
            nonlocal silence_start, has_spoken

            if status:
                print(f"[Microphone] {status}")

            audio = indata.copy()
            frames.append(audio)

            rms = float(np.sqrt(np.mean(np.square(audio))))
            level = min(1.0, rms * 8.0)

            if level_callback:
                level_callback(level)

            if rms >= self.silence_threshold:
                has_spoken = True
                silence_start = None
            elif has_spoken and silence_start is None:
                silence_start = time.time()

        print(
            f"[STT] Opening microphone device {MIC_DEVICE} "
            f"@ {self.sample_rate} Hz"
        )

        with sd.InputStream(
            device=MIC_DEVICE,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            callback=callback,
        ):
            while True:
                elapsed = time.time() - start_time

                if elapsed >= self.max_duration:
                    break

                if (
                    has_spoken
                    and silence_start is not None
                    and (time.time() - silence_start) >= self.silence_duration
                ):
                    break

                time.sleep(0.05)

        if not frames or not has_spoken:
            return None

        audio = np.squeeze(np.concatenate(frames, axis=0))
        audio = np.clip(audio, -1.0, 1.0)

        # SpeechRecognition's AudioData below is configured for 16 kHz.
        # Capture at the microphone's native 48 kHz, then resample once here.
        audio_16k = resample_poly(audio, WAKE_SAMPLE_RATE, MIC_SAMPLE_RATE)
        audio_int16 = (np.clip(audio_16k, -1.0, 1.0) * 32767).astype(np.int16)

        return audio_int16.tobytes()

    def transcribe(self, audio_bytes) -> str:
        if not audio_bytes:
            return ""

        audio_data = sr.AudioData(
            audio_bytes,
            WAKE_SAMPLE_RATE,
            2,
        )

        try:
            text = self.recognizer.recognize_google(audio_data)
            return text.strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            raise RuntimeError(f"Speech recognition service unavailable: {e}")
