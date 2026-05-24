# ============================================================
# FILE: utils/audio_utils.py
#
# PURPOSE:
#   Shared audio helper functions used by services/audio_capture.py.
#   Keeps silence detection and WAV file writing out of the capture
#   service so each function does exactly one thing (SKILL.md 1.2).
#
# INPUTS:
#   - audio_chunk (bytes): a single pyaudio buffer frame
#   - audio_data (list[bytes]): all recorded frames concatenated
#   - path (Path): destination path for the WAV file
#   - sample_rate (int): Hz — must match SAMPLE_RATE in config.py
#   - channels (int): 1 = mono, 2 = stereo
#
# OUTPUTS:
#   - is_silent → bool: True if chunk is below amplitude threshold
#   - save_wav  → bool: True if file written successfully, else False
#
# DEPENDENCIES:
#   - numpy (pip install numpy — RMS calculation; audioop removed in Python 3.13)
#   - wave  (Python standard library — writes WAV headers)
#   - utils/logger.py
#
# CALLED BY:
#   - services/audio_capture.py
#
# AUTHOR: Clip Project
# LAST UPDATED: 2026-05-23
# ============================================================

import wave
from pathlib import Path

import numpy as np

from utils.logger import get_logger

# audioop was removed in Python 3.13. RMS amplitude is computed with
# numpy instead: interpret the raw bytes as 16-bit signed PCM integers,
# cast to float32 to avoid overflow during squaring, then take sqrt(mean).
# The result is numerically equivalent to audioop.rms(chunk, 2).

logger = get_logger(__name__)


def is_silent(audio_chunk: bytes, threshold: int = 500) -> bool:
    """
    Returns True if the RMS amplitude of an audio chunk is below threshold.

    Steps:
      1. Interpret the raw bytes as an array of 16-bit signed PCM samples.
      2. Cast to float32 before squaring to prevent integer overflow.
      3. Compute RMS: sqrt(mean(samples ** 2)).
      4. Compare RMS against the threshold value.
      5. Return True (silent) or False (speech present).

    Args:
        audio_chunk (bytes): A single buffer frame from pyaudio.
                             Example: stream.read(1024)
        threshold (int):     RMS amplitude below which audio is considered
                             silent. 500 works well for most environments;
                             raise it (e.g. 800) in noisy rooms.
                             Default: 500

    Returns:
        bool: True  → chunk is silent (below threshold).
              False → chunk contains speech or loud sound.

    Example:
        chunk = stream.read(1024)
        if is_silent(chunk, threshold=500):
            silence_frames += 1
    """
    # np.frombuffer re-uses the bytes buffer without copying.
    # dtype=np.int16 matches pyaudio.paInt16 used in audio_capture.py.
    audio_array = np.frombuffer(audio_chunk, dtype=np.int16)

    # Cast to float32 before squaring — int16 values up to 32767 would
    # overflow if squared as integers (32767² = 1,073,741,289 > int16 max).
    rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))

    return float(rms) < threshold


def save_wav(
    audio_data: list,
    path: Path,
    sample_rate: int,
    channels: int,
) -> bool:
    """
    Writes a list of raw PCM byte frames to a WAV file on disk.

    Steps:
      1. Open the destination path for writing in binary mode.
      2. Configure WAV file headers: channels, sample width, frame rate.
      3. Write all recorded frames as a single byte string.
      4. Close the file (wave.Wave_write is used as a context manager).
      5. Log success and return True, or log error and return False.

    Args:
        audio_data (list[bytes]): All recorded pyaudio frames collected
                                  during a recording session.
                                  Example: [b'\x00\x01...', b'\x00\x02...']
        path (Path):              Destination file path.
                                  Example: Path("temp") / "input.wav"
        sample_rate (int):        Samples per second. Must be 16000 for
                                  Whisper. Example: 16000
        channels (int):           Number of audio channels. Must be 1
                                  (mono) for Whisper. Example: 1

    Returns:
        bool: True  → file written successfully.
              False → write failed (permission error, disk full, etc.).

    Example:
        success = save_wav(frames, Path("temp/input.wav"), 16000, 1)
        if not success:
            return None  # skip this recording cycle
    """
    try:
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(channels)

            # sample_width=2 → 16-bit PCM, matching pyaudio.paInt16.
            # This must stay in sync with the format used in AudioCapture.
            wav_file.setsampwidth(2)

            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"".join(audio_data))

        logger.info("Audio saved to %s", path)
        return True

    except OSError as e:
        logger.error(
            "Failed to write WAV file to %s: %s\n"
            "Fix: Check that the temp/ directory exists and is writable.",
            path,
            e,
        )
        return False
