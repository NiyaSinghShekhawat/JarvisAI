import importlib.util


class LocalWakeWordDetector:
    """Local openWakeWord detector for the bundled Hey Jarvis model.

    "Wake up Jarvis" is intentionally not passed to openWakeWord because it
    is not a bundled pretrained model. It can be added later as a custom model
    without changing the microphone pipeline.
    """

    MODEL_NAME = "hey_jarvis"
    PHRASE = "Hey Jarvis"

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

            self.model = Model(wakeword_models=[self.MODEL_NAME])
            self.enabled = True

            print("[WAKE] Local wake-word engine loaded.")
            print(f"[WAKE] Model: {self.MODEL_NAME}")
            print(f"[WAKE] Threshold: {self.threshold:.2f}")
            print(f"[WAKE] Phrase: '{self.PHRASE}'")
            print("[WAKE] Note: 'Wake up Jarvis' requires a custom wake-word model.")

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

            scores = self.model.predict(samples)
            score = float(scores.get(self.MODEL_NAME, 0.0))

            if score >= self.threshold:
                print(f"[WAKE] '{self.PHRASE}' detected ({score:.2f})")
                return True

        except Exception as exc:
            if not self._warned:
                print(f"[WAKE] Local detector error: {exc}")
                self._warned = True

        return False
