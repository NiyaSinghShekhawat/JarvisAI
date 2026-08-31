import time
import numpy as np


class ClapDetector:
    """Short-window transient detector for a double-clap wake gesture."""

    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.frame_samples = int(sample_rate * 0.02)  # 20 ms
        self.history = []
        self.first_clap_time = None
        self.last_candidate = 0.0
        self.cooldown_until = 0.0
        self.noise_rms = 0.0005
        self.noise_peak = 0.002

        self.min_gap = 0.16
        self.max_gap = 0.65
        self.cooldown = 2.0

    def calibrate(self, audio):
        audio = np.asarray(audio, dtype=np.float32).flatten()
        if audio.size == 0:
            return
        frames = self._frames(audio)
        if not frames:
            return
        rms = np.array([self._rms(f) for f in frames])
        peak = np.array([np.max(np.abs(f)) for f in frames])
        self.noise_rms = max(0.0002, float(np.percentile(rms, 85)))
        self.noise_peak = max(0.001, float(np.percentile(peak, 85)))

    def process(self, audio):
        """Return True only when two transient candidates form a double clap."""
        audio = np.asarray(audio, dtype=np.float32).flatten()
        if audio.size == 0:
            return False

        self.history.extend(audio.tolist())
        if len(self.history) > self.frame_samples * 8:
            self.history = self.history[-self.frame_samples * 8:]

        triggered = False
        samples = np.asarray(self.history, dtype=np.float32)

        while len(samples) >= self.frame_samples:
            frame = samples[:self.frame_samples]
            samples = samples[self.frame_samples:]
            if self._candidate(frame):
                now = time.monotonic()
                if now < self.cooldown_until:
                    continue
                if self.first_clap_time is None:
                    self.first_clap_time = now
                else:
                    gap = now - self.first_clap_time
                    if self.min_gap <= gap <= self.max_gap:
                        triggered = True
                        self.first_clap_time = None
                        self.cooldown_until = now + self.cooldown
                    elif gap > self.max_gap:
                        self.first_clap_time = now

        self.history = samples.tolist()
        return triggered

    def _candidate(self, frame):
        rms = self._rms(frame)
        peak = float(np.max(np.abs(frame)))
        if peak <= 0:
            return False

        # Speech is typically sustained over multiple frames. A clap is a
        # broadband transient with a steep energy jump and rapid decay.
        if rms < max(0.025, self.noise_rms * 8.0):
            return False
        if peak < max(0.30, self.noise_peak * 8.0):
            return False
        if peak / max(rms, 1e-6) < 3.0:
            return False

        spectrum = np.abs(np.fft.rfft(frame * np.hanning(len(frame))))
        freqs = np.fft.rfftfreq(len(frame), 1 / self.sample_rate)
        total = np.sum(spectrum) + 1e-9
        high = np.sum(spectrum[freqs >= 2500]) / total

        # Reject low-frequency voice-heavy frames.
        if high < 0.22:
            return False

        return True

    @staticmethod
    def _rms(frame):
        return float(np.sqrt(np.mean(np.square(frame))) + 1e-12)

    def _frames(self, audio):
        return [audio[i:i + self.frame_samples]
                for i in range(0, len(audio) - self.frame_samples + 1, self.frame_samples)]
