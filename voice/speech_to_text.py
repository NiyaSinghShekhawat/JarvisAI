import time
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
import speech_recognition as sr


class SpeechToText:
    """
    Microphone capture + speech recognition.

    Pipeline:

        Microphone
            ↓
        sounddevice
            ↓
        Voice activity detection
            ↓
        Google Speech Recognition
            ↓
        Text transcript
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
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

    # ========================================================
    # RECORD UNTIL SILENCE
    # ========================================================

    def record_until_silence(
        self,
        level_callback: Optional[
            Callable[[float], None]
        ] = None,
    ):
        """
        Record until the user stops speaking.

        The microphone remains active until:
        - the user speaks and then becomes silent
        - OR max_duration is reached.
        """

        frames: list[np.ndarray] = []

        # These variables MUST be inside this method.
        silence_start: Optional[float] = None
        has_spoken: bool = False
        start_time: float = time.time()

        # ====================================================
        # MICROPHONE CALLBACK
        # ====================================================

        def callback(
            indata: np.ndarray,
            frame_count: int,
            time_info,
            status,
        ) -> None:

            nonlocal silence_start
            nonlocal has_spoken

            if status:
                print(
                    f"[Microphone] {status}"
                )

            # Copy current microphone frame
            audio = indata.copy()

            frames.append(audio)

            # =================================================
            # RMS AMPLITUDE
            # =================================================

            rms: float = float(
                np.sqrt(
                    np.mean(
                        np.square(audio)
                    )
                )
            )

            # Convert microphone level to approximately 0-1
            level: float = min(
                1.0,
                rms * 8.0
            )

            # Send level to UI
            if level_callback:
                level_callback(level)

            # =================================================
            # SPEECH DETECTION
            # =================================================

            if rms >= self.silence_threshold:

                # User is speaking
                has_spoken = True

                # Reset silence timer
                silence_start = None

            else:

                # Only detect ending silence after
                # the user has actually spoken.
                if has_spoken:

                    if silence_start is None:
                        silence_start = time.time()

        # ====================================================
        # OPEN MICROPHONE
        # ====================================================

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            callback=callback,
        ):

            while True:

                elapsed: float = (
                    time.time() - start_time
                )

                # ------------------------------------------------
                # Maximum recording duration
                # ------------------------------------------------

                if elapsed >= self.max_duration:
                    break

                # ------------------------------------------------
                # User stopped speaking
                # ------------------------------------------------

                if (
                    has_spoken
                    and
                    silence_start is not None
                    and
                    (
                        time.time()
                        - silence_start
                    ) >= self.silence_duration
                ):
                    break

                time.sleep(0.05)

        # ====================================================
        # NO SPEECH DETECTED
        # ====================================================

        if not frames or not has_spoken:
            return None

        # ====================================================
        # JOIN AUDIO
        # ====================================================

        audio = np.concatenate(
            frames,
            axis=0
        )

        audio = np.squeeze(audio)

        # ====================================================
        # FLOAT32 → PCM16
        # ====================================================

        audio = np.clip(
            audio,
            -1.0,
            1.0
        )

        audio_int16 = (
            audio * 32767
        ).astype(np.int16)

        return audio_int16.tobytes()

    # ========================================================
    # TRANSCRIBE
    # ========================================================

    def transcribe(
        self,
        audio_bytes,
    ) -> str:

        if not audio_bytes:
            return ""

        audio_data = sr.AudioData(
            audio_bytes,
            self.sample_rate,
            2,
        )

        try:

            text = (
                self.recognizer
                .recognize_google(
                    audio_data
                )
            )

            return text.strip()

        except sr.UnknownValueError:

            return ""

        except sr.RequestError as e:

            raise RuntimeError(
                "Speech recognition service "
                f"unavailable: {e}"
            )