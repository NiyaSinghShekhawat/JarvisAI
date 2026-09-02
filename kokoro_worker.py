import json
import os
import sys
import tempfile

import numpy as np
import soundfile as sf
from kokoro import KPipeline


VOICE = "am_adam"
SAMPLE_RATE = 24000


def log(message):
    """Write diagnostics to stderr without affecting the stdout protocol."""
    try:
        print(message, file=sys.stderr, flush=True)
    except (OSError, ValueError):
        pass


log("[KOKORO] Loading Kokoro model...")
pipeline = KPipeline(
    lang_code="a",
    repo_id="hexgrad/Kokoro-82M",
)
log(f"[KOKORO] Ready. Voice: {VOICE}")

# stdout is a strict JSON-lines protocol used by voice/text_to_speech.py.
# The first message is the readiness handshake, emitted only after the model
# has finished loading.
try:
    print(json.dumps({"ready": True, "voice": VOICE}), flush=True)
except (OSError, ValueError):
    sys.exit(1)


def synthesize(text):
    chunks = []
    generator = pipeline(text, voice=VOICE)

    for _, _, audio in generator:
        chunks.append(audio)

    if not chunks:
        raise RuntimeError("Kokoro generated no audio.")

    audio = np.concatenate(chunks)
    fd, path = tempfile.mkstemp(
        suffix=".wav",
        prefix="jarvis_kokoro_",
    )
    os.close(fd)

    sf.write(path, audio, SAMPLE_RATE)
    return path


for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    try:
        request = json.loads(line)
        command = request.get("command")

        if command == "speak":
            text = request.get("text", "").strip()
            if not text:
                print(json.dumps({"error": "Empty text"}), flush=True)
                continue

            path = synthesize(text)
            print(json.dumps({"audio": path}), flush=True)

        elif command == "shutdown":
            break

        else:
            print(
                json.dumps({"error": f"Unknown command: {command}"}),
                flush=True,
            )

    except Exception as e:
        log(f"[KOKORO ERROR] {e}")
        try:
            print(json.dumps({"error": str(e)}), flush=True)
        except (OSError, ValueError):
            break
