# ============================================================
# FILE: services/audio_capture.py
#
# PURPOSE:
#   Records audio from the microphone until silence is detected,
#   then saves the recording as a 16kHz mono WAV file for Whisper.
#   Handles pyaudio initialisation, frame buffering, silence
#   detection, and file saving — all in one focused class.
#
# INPUTS:
#   - Microphone audio (system default or MIC_DEVICE_INDEX)
#
# OUTPUTS:
#   - audio_path (str): path to saved WAV file, e.g. "temp/input.wav"
#   - None: if recording is too short or mic fails
#
# DEPENDENCIES:
#   - pyaudio (pip install pyaudio; requires: brew install portaudio)
#   - config.py → SAMPLE_RATE, CHANNELS, SILENCE_THRESHOLD_SECS,
#                 MIN_RECORDING_SECS, MIC_DEVICE_INDEX, TEMP_INPUT_AUDIO
#   - utils/logger.py
#   - utils/audio_utils.py
#
# CALLED BY:
#   - main.py → forward_pipeline(), reply_pipeline()
#
# AUTHOR: Clip Project
# LAST UPDATED: 2026-05-23
# ============================================================

import pyaudio

import config
from utils.audio_utils import is_silent, save_wav
from utils.logger import get_logger

# pyaudio reads audio in fixed-size chunks called frames.
# 1024 frames at 16kHz = ~64ms per read — short enough to
# detect silence quickly without burning CPU on tiny reads.
_FRAMES_PER_BUFFER = 1024

# Silence amplitude threshold passed to is_silent().
# 500 RMS works well in a quiet home environment.
# Raise to 800+ if false triggers occur in a noisy room.
_SILENCE_AMPLITUDE = 500


class AudioCapture:
    """
    Records microphone audio until silence is detected.

    Keeps pyaudio and config values as instance state so the
    caller (main.py) does not need to manage audio resources.
    Create once at startup; call capture_audio() in the loop.
    """

    def __init__(self) -> None:
        """
        Loads config values and initialises the logger.

        Steps:
          1. Store all config constants needed for recording.
          2. Calculate the silence frame count from threshold seconds
             so the capture loop can compare against a plain integer.
          3. Initialise the logger for this module.

        Args:
            None

        Returns:
            None
        """
        self.sample_rate    = config.SAMPLE_RATE
        self.channels       = config.CHANNELS
        self.mic_index      = config.MIC_DEVICE_INDEX
        self.output_path    = config.TEMP_INPUT_AUDIO
        self.min_secs       = config.MIN_RECORDING_SECS

        # Convert silence threshold from seconds to a frame count.
        # The capture loop counts consecutive silent frames; comparing
        # against a pre-computed integer is cheaper than dividing each loop.
        self.silence_frames = int(
            config.SILENCE_THRESHOLD_SECS * self.sample_rate / _FRAMES_PER_BUFFER
        )

        self.logger = get_logger(__name__)

    def capture_audio(self) -> str | None:
        """
        Records from the mic until silence is detected, saves to WAV.

        Steps:
          1. Open a pyaudio stream on the configured mic device.
          2. Wait for the first non-silent frame (speech start).
          3. Buffer all frames until SILENCE_THRESHOLD_SECS of continuous
             silence is detected — this marks the end of the utterance.
          4. Reject recordings shorter than MIN_RECORDING_SECS.
          5. Save buffered frames to TEMP_INPUT_AUDIO via save_wav().
          6. Return the file path as a string for the next pipeline step.

        Args:
            None

        Returns:
            str:  Path to the saved WAV file.
                  Example: "temp/input.wav"
            None: If the recording is too short, the mic fails to open,
                  or the WAV file cannot be written.

        Example:
            capture = AudioCapture()
            path = capture.capture_audio()
            if path:
                transcript = transcribe_audio(path)
        """
        audio = pyaudio.PyAudio()
        stream = self._open_stream(audio)

        if stream is None:
            audio.terminate()
            return None

        self.logger.info("Listening for speech...")

        frames = []
        silent_frame_count = 0
        speech_detected = False

        try:
            while True:
                chunk = stream.read(_FRAMES_PER_BUFFER, exception_on_overflow=False)
                silent = is_silent(chunk, _SILENCE_AMPLITUDE)

                if not speech_detected:
                    if not silent:
                        # First loud frame — the speaker has started talking.
                        self.logger.info("Speech detected.")
                        speech_detected = True
                        frames.append(chunk)
                    # Still waiting for speech — discard silent pre-roll frames.
                    continue

                # Speech is in progress — buffer every frame.
                frames.append(chunk)

                if silent:
                    silent_frame_count += 1
                else:
                    # Non-silent frame resets the silence counter.
                    # This prevents pauses mid-sentence from cutting off early.
                    silent_frame_count = 0

                # 1.5s of silence is the end-of-utterance signal.
                # Why 1.5s: shorter values cut off natural speech pauses
                # mid-sentence; longer values make the pipeline feel laggy.
                if silent_frame_count >= self.silence_frames:
                    self.logger.info("Silence detected — processing.")
                    break

        finally:
            # Always close the stream, even if an exception occurs above.
            stream.stop_stream()
            stream.close()
            audio.terminate()

        return self._validate_and_save(frames)

    def _open_stream(self, audio: pyaudio.PyAudio) -> pyaudio.Stream | None:
        """
        Opens a pyaudio input stream on the configured mic device.

        Steps:
          1. Call audio.open() with project audio settings.
          2. On failure, log a human-readable error with a Fix message.
          3. Return the stream, or None if it could not be opened.

        Args:
            audio (pyaudio.PyAudio): Initialised PyAudio instance.

        Returns:
            pyaudio.Stream: Open input stream ready to read frames.
            None:           If the device is unavailable or misconfigured.

        Example:
            stream = self._open_stream(audio)
            if stream is None:
                return None
        """
        try:
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.mic_index,
                frames_per_buffer=_FRAMES_PER_BUFFER,
            )
            return stream

        except OSError as e:
            self.logger.error(
                "Could not open microphone (device index: %s): %s\n"
                "Fix: Run 'python utils/list_audio_devices.py' to see available "
                "devices, then set MIC_DEVICE_INDEX in config.py.",
                self.mic_index,
                e,
            )
            return None

    def _validate_and_save(self, frames: list) -> str | None:
        """
        Checks minimum recording length, then writes frames to WAV.

        Steps:
          1. Calculate the duration of the recording from frame count.
          2. If shorter than MIN_RECORDING_SECS, log and return None.
          3. Call save_wav() to write the file.
          4. Return the file path as a string on success.

        Args:
            frames (list[bytes]): All buffered pyaudio frames.

        Returns:
            str:  Path to the saved WAV file. Example: "temp/input.wav"
            None: If recording too short or file write failed.

        Example:
            path = self._validate_and_save(frames)
        """
        duration_secs = len(frames) * _FRAMES_PER_BUFFER / self.sample_rate

        if duration_secs < self.min_secs:
            self.logger.info(
                "Recording too short (%.2fs < %.2fs), skipping.",
                duration_secs,
                self.min_secs,
            )
            return None

        saved = save_wav(frames, self.output_path, self.sample_rate, self.channels)

        if not saved:
            return None

        return str(self.output_path)
