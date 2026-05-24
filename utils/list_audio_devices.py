# ============================================================
# FILE: utils/list_audio_devices.py
#
# PURPOSE:
#   Prints all available audio input (microphone) devices and
#   their index numbers. Run this to find the correct value for
#   MIC_DEVICE_INDEX in config.py when the default mic is wrong.
#
# INPUTS:
#   None (run directly: python utils/list_audio_devices.py)
#
# OUTPUTS:
#   - Printed list of device indices and names to terminal
#
# DEPENDENCIES:
#   - pyaudio (pip install pyaudio; requires: brew install portaudio)
#
# CALLED BY:
#   - User directly, not imported by any module
#
# AUTHOR: Clip Project
# LAST UPDATED: 2026-05-23
# ============================================================

# ──────────────────────────────────────────────────────────────
# HOW TO USE THIS SCRIPT
#
# Run if your mic is not being detected, or if LingoBridge is
# recording from the wrong device (e.g. a webcam mic instead of
# a dedicated USB mic).
#
#   python utils/list_audio_devices.py
#
# Look for your microphone in the printed list.
# Copy its index number to MIC_DEVICE_INDEX in config.py.
#
# Example output:
#   Index 0 — Built-in Microphone (maxInputChannels: 1)
#   Index 1 — USB Audio Device    (maxInputChannels: 2)  ← use this
#
# Then in config.py set:
#   MIC_DEVICE_INDEX = 1
# ──────────────────────────────────────────────────────────────

import pyaudio


def list_input_devices() -> None:
    """
    Prints all audio input devices available on this machine.

    Steps:
      1. Initialise a pyaudio instance to query the system.
      2. Iterate over all device indices reported by PortAudio.
      3. Skip devices that have no input channels (output-only devices).
      4. Print index, name, and max input channel count for each mic.
      5. Terminate the pyaudio instance to release system resources.

    Args:
        None

    Returns:
        None

    Example:
        list_input_devices()
        # Index 0 — Built-in Microphone     (maxInputChannels: 1)
        # Index 2 — USB Audio CODEC          (maxInputChannels: 2)
    """
    audio = pyaudio.PyAudio()

    device_count = audio.get_device_count()
    print(f"\nFound {device_count} audio device(s). Input devices only:\n")

    found_any = False

    for index in range(device_count):
        device_info = audio.get_device_info_by_index(index)

        # Skip output-only devices — they cannot be used as microphones.
        if device_info["maxInputChannels"] < 1:
            continue

        found_any = True
        name = device_info["name"]
        max_channels = device_info["maxInputChannels"]
        print(f"  Index {index} — {name} (maxInputChannels: {max_channels})")

    if not found_any:
        print("  No input devices found.")
        print("  Fix: Check that a microphone is connected and recognised by macOS.")

    print(
        "\nTo use a specific mic, set MIC_DEVICE_INDEX = <index> in config.py\n"
        "Leave MIC_DEVICE_INDEX = None to use the system default.\n"
    )

    # Always terminate to free PortAudio resources — not doing so
    # can leave ghost audio sessions that block future recordings.
    audio.terminate()


if __name__ == "__main__":
    list_input_devices()
