import sys
import json
import tempfile
import os

import numpy as np
import soundfile as sf
from kokoro import KPipeline


print("[KOKORO] Loading Kokoro model...", file=sys.stderr)

pipeline = KPipeline(
    lang_code="a",
    repo_id="hexgrad/Kokoro-82M",
)

VOICE = "am_adam"
SAMPLE_RATE = 24000

print(f"[KOKORO] Ready. Voice: {VOICE}", file=sys.stderr)


def synthesize(text):
    chunks = []

    generator = pipeline(
        text,
        voice=VOICE,
    )

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

    sf.write(
        path,
        audio,
        SAMPLE_RATE,
    )

    return path


for line in sys.stdin:
    line = line.strip()

    if not line:
        continue

    try:
        request = json.loads(line)

        if request.get("command") == "speak":
            text = request.get("text", "").strip()

            if not text:
                print(
                    json.dumps({"error": "Empty text"}),
                    flush=True,
                )
                continue

            path = synthesize(text)

            print(
                json.dumps({
                    "audio": path,
                }),
                flush=True,
            )

        elif request.get("command") == "shutdown":
            break

    except Exception as e:
        print(
            json.dumps({
                "error": str(e),
            }),
            flush=True,
        )