import importlib.util


class LocalWakeWordDetector:
    """Local wake-word adapter.

    Uses openWakeWord when installed. No network transcription is performed.
    The model is loaded lazily so Jarvis can still start with clap-only wake
    if the optional dependency/model is not installed yet.
    """

    def __init__(self, phrase="hey jarvis", threshold=0.55):
        self.phrase = phrase
        self.threshold = threshold
        self.model = None
        self.enabled = False
        self._warned = False
        self._try_load()

    def _try_load(self):
        if importlib.util.find_spec("openwakeword") is None:
            return
        try:
            from openwakeword.model import Model
            self.model = Model()
            self.enabled = True
            print("[WAKE] Local wake-word engine loaded.")
        except Exception as exc:
            print(f"[WAKE] Local wake-word engine unavailable: {exc}")

    def process(self, audio):
        if not self.enabled or self.model is None:
            return False

        try:
            import numpy as np
            samples = np.asarray(audio, dtype=np.int16).flatten()
            if samples.size == 0:
                return False
            scores = self.model.predict(samples)
            for name, score in scores.items():
                if self.phrase.lower() in name.lower() and float(score) >= self.threshold:
                    print(f"[WAKE] Local wake word detected: {name} ({score:.2f})")
                    return True
        except Exception as exc:
            if not self._warned:
                print(f"[WAKE] Local detector error: {exc}")
                self._warned = True
        return False
