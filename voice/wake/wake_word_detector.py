import importlib.util


class LocalWakeWordDetector:
    """Local ``Hey Jarvis`` detector backed by openWakeWord.

    This class owns only wake-word inference. Microphone ownership stays in
    ``voice.wake.listener.WakeListener`` so the application has one passive
    microphone pipeline.
    """

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

            # Load ONLY the Jarvis model. Loading every bundled wake word makes
            # the result ambiguous and wastes CPU on every microphone frame.
            self.model = Model(wakeword_models=["hey_jarvis"])
            self.enabled = True

            print("[WAKE] Local wake-word engine loaded.")
            print(f"[WAKE] Models: {list(self.model.models.keys())}")
            print(f"[WAKE] Threshold: {self.threshold:.2f}")

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
                threshold={"hey_jarvis": self.threshold},
                debounce_time=1.0,
            )

            score = float(scores.get("hey_jarvis", 0.0))

            if score >= self.threshold:
                print(f"[WAKE] 'Hey Jarvis' detected ({score:.2f})")
                return True

        except Exception as exc:
            if not self._warned:
                print(f"[WAKE] Local detector error: {exc}")
                self._warned = True

        return False
