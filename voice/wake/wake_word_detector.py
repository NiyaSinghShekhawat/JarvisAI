import importlib.util


class LocalWakeWordDetector:
    """Local wake-word detector backed by openWakeWord.

    Supports both "Hey Jarvis" and "Wake up Jarvis". Microphone ownership
    remains in WakeListener so the application keeps one passive audio stream.
    """

    WAKE_WORDS = {
        "hey_jarvis": "Hey Jarvis",
        "wake_up_jarvis": "Wake up Jarvis",
    }

    def __init__(self, threshold=0.55):
        self.threshold = threshold
        self.model = None
        self.enabled = False
        self._warned = False
        self._try_load()

    def _try_load(self):
        if importlib.util.find_spec("openwakeword") is None:
            print("[WAKE] openWakeWord is not installed; voice wake disabled.")
            return

        try:
            from openwakeword.model import Model

            # Load only the two Jarvis wake-word models.
            self.model = Model(wakeword_models=list(self.WAKE_WORDS.keys()))
            self.enabled = True

            print("[WAKE] Local wake-word engine loaded.")
            print(f"[WAKE] Models: {list(self.model.models.keys())}")
            print(f"[WAKE] Threshold: {self.threshold:.2f}")
            print("[WAKE] Phrases: 'Hey Jarvis' / 'Wake up Jarvis'")

        except Exception as exc:
            print(f"[WAKE] Local wake-word engine unavailable: {exc}")

    def process(self, audio):
        """Process 16-bit 16 kHz mono PCM and return True on detection."""
        if not self.enabled or self.model is None:
            return False

        try:
            import numpy as np

            samples = np.asarray(audio, dtype=np.int16).flatten()
            if samples.size == 0:
                return False

            scores = self.model.predict(
                samples,
                threshold={name: self.threshold for name in self.WAKE_WORDS},
                debounce_time=1.0,
            )

            for model_name, phrase in self.WAKE_WORDS.items():
                score = float(scores.get(model_name, 0.0))
                if score >= self.threshold:
                    print(f"[WAKE] '{phrase}' detected ({score:.2f})")
                    return True

        except Exception as exc:
            if not self._warned:
                print(f"[WAKE] Local detector error: {exc}")
                self._warned = True

        return False
