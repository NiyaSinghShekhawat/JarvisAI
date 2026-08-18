import sys
import time

import numpy as np
import sounddevice as sd


def test_device(device_index):

    device = sd.query_devices(device_index)

    print("\n" + "=" * 60)
    print(f"DEVICE {device_index}")
    print("=" * 60)

    print(f"Name: {device['name']}")
    print(f"Input channels: {device['max_input_channels']}")
    print(f"Sample rate: {device['default_samplerate']}")

    samplerate = int(device["default_samplerate"])

    def callback(indata, frames, time_info, status):

        if status:
            print(
                f"\nSTATUS: {status}"
            )

        # Use first channel
        audio = indata[:, 0]

        rms = float(
            np.sqrt(
                np.mean(
                    np.square(audio)
                )
            )
        )

        peak = float(
            np.max(
                np.abs(audio)
            )
        )

        print(
            f"RMS={rms:.5f} | PEAK={peak:.5f}",
            end="\r"
        )

    try:

        with sd.InputStream(
            device=device_index,
            samplerate=samplerate,
            channels=1,
            dtype="float32",
            callback=callback,
        ):

            print()
            print("Speak normally.")
            print("Then clap twice.")
            print("Testing for 8 seconds...")
            print()

            time.sleep(8)

        print("\nFinished.")

    except Exception as e:

        print()
        print(
            f"ERROR: {type(e).__name__}: {e}"
        )


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            "\nUsage:"
        )

        print(
            "python -m voice.mic_test DEVICE_NUMBER"
        )

        print(
            "\nExample:"
        )

        print(
            "python -m voice.mic_test 1"
        )

        sys.exit(1)

    try:

        device_index = int(
            sys.argv[1]
        )

    except ValueError:

        print(
            "Device number must be an integer."
        )

        sys.exit(1)

    test_device(
        device_index
    )