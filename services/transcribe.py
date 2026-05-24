# ============================================================
# FILE: services/transcribe.py
#
# PURPOSE:
#   Loads the local faster-whisper model and transcribes a WAV
#   audio file to text. Returns the transcript only if the detected
#   language is Mandarin Chinese ("zh") — all other languages are
#   rejected to prevent mistranslation in the pipeline.
#
# INPUTS:
#   - audio_path (str): path to a 16kHz mono WAV file
#
# OUTPUTS:
#   - transcript (str): Mandarin text, e.g. "你今天吃饭了吗？"
#   - None: if language is not Mandarin, audio file missing, or
#           Whisper fails to run
#
# DEPENDENCIES:
#   - faster-whisper (pip install faster-whisper)
#   - config.py → WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE,
#                 MANDARIN_LANGUAGE_CODE
#   - utils/logger.py
#
# CALLED BY:
#   - main.py → forward_pipeline(), reply_pipeline()
#
# AUTHOR: Clip Project
# LAST UPDATED: 2026-05-23
# ============================================================

from pathlib import Path

from faster_whisper import WhisperModel

import config
from utils.logger import get_logger


class Transcriber:
    """
    Loads the faster-whisper model and transcribes audio files.

    The model is loaded once at __init__ time so it stays resident
    in memory across multiple pipeline cycles. Loading it fresh on
    every recording would add 3-5 seconds of latency per cycle.
    """

    def __init__(self) -> None:
        """
        Loads the faster-whisper model into memory.

        Steps:
          1. Initialise the logger for this module.
          2. Log the model name and device so the owner can confirm
             which model is running.
          3. Load WhisperModel with settings from config.py.
          4. On failure, log a human-readable error and set
             self.model = None so transcribe_audio() fails gracefully.

        Args:
            None

        Returns:
            None
        """
        self.logger = get_logger(__name__)
        self.model = None

        self.logger.info(
            "Loading Whisper model '%s' on device='%s' compute_type='%s'...",
            config.WHISPER_MODEL,
            config.WHISPER_DEVICE,
            config.WHISPER_COMPUTE_TYPE,
        )

        try:
            # device="cpu" is required on Mac M4.
            # faster-whisper does not support Apple Metal (MPS/CoreML) —
            # passing "mps" or "gpu" raises an error at runtime.
            # On Brahma (AMD ROCm), "cuda" maps to HIP automatically.
            # Controlled via WHISPER_DEVICE in config.py so this file
            # never needs to change between environments.
            self.model = WhisperModel(
                config.WHISPER_MODEL,
                device=config.WHISPER_DEVICE,
                compute_type=config.WHISPER_COMPUTE_TYPE,
            )
            self.logger.info("Whisper model loaded successfully.")

        except Exception as e:
            self.logger.error(
                "Failed to load Whisper model '%s': %s\n"
                "Fix: Run 'pip install faster-whisper' and confirm the model "
                "name is correct in config.py.",
                config.WHISPER_MODEL,
                e,
            )

    def transcribe_audio(self, audio_path: str) -> str | None:
        """
        Transcribes a WAV file and returns Mandarin text, or None.

        Steps:
          1. Check the model loaded successfully at startup.
          2. Check the audio file exists on disk.
          3. Run Whisper transcription with language detection.
          4. Log detected language and confidence score.
          5. Reject non-Mandarin audio — return None if language != "zh".
          6. Collect all segment texts, join, and return as one string.

        Args:
            audio_path (str): Full or relative path to a 16kHz mono WAV.
                              Example: "temp/input.wav"

        Returns:
            str:  Mandarin transcript if language is Chinese.
                  Example: "你今天吃饭了吗？"
            None: If audio is not Mandarin, file is missing, model
                  failed to load, or Whisper raises an exception.

        Example:
            transcriber = Transcriber()
            result = transcriber.transcribe_audio("temp/input.wav")
            if result:
                print(f"MIL said: {result}")
        """
        # Step 1: Abort early if the model never loaded.
        if self.model is None:
            self.logger.error(
                "Whisper model is not loaded — cannot transcribe.\n"
                "Fix: Check the startup error above and restart the pipeline."
            )
            return None

        # Step 2: Confirm the audio file exists before calling Whisper.
        # A missing file would produce a cryptic C-level error from faster-whisper.
        if not Path(audio_path).exists():
            self.logger.error(
                "Audio file not found: %s\n"
                "Fix: Check that audio_capture.py saved the file correctly.",
                audio_path,
            )
            return None

        # Step 3: Run Whisper transcription.
        segments, info = self._run_whisper(audio_path)
        if segments is None:
            return None

        # Step 4: Log detected language and confidence.
        self.logger.info(
            "Detected language: %s (confidence: %.2f)",
            info.language,
            info.language_probability,
        )

        # Step 5: Reject non-Mandarin audio.
        # Without this check, English or other speech overheard by the mic
        # would flow through the pipeline and produce nonsense translations.
        # We only want to forward what MIL says in Mandarin.
        if info.language != config.MANDARIN_LANGUAGE_CODE:
            self.logger.info(
                "Non-Mandarin audio detected (%s) — skipping.",
                info.language,
            )
            return None

        # Step 6: Collect all segment texts into a single transcript string.
        # Whisper returns results as a generator of segments — consume it fully.
        transcript = " ".join(segment.text.strip() for segment in segments)

        if not transcript.strip():
            self.logger.info("Transcript is empty after joining segments — skipping.")
            return None

        self.logger.info("Transcript: %s", transcript)
        return transcript

    def _run_whisper(self, audio_path: str):
        """
        Calls the faster-whisper model and returns (segments, info).

        Isolated so that transcribe_audio() stays under 40 lines and
        the try/except does not swallow unrelated logic (SKILL.md 6.1).

        Steps:
          1. Call model.transcribe() with the audio file path.
          2. On success, return the (segments generator, TranscriptionInfo).
          3. On failure, log a human-readable error and return (None, None).

        Args:
            audio_path (str): Path to the WAV file to transcribe.

        Returns:
            tuple(generator, TranscriptionInfo): Whisper output on success.
            tuple(None, None):                   On any transcription error.

        Example:
            segments, info = self._run_whisper("temp/input.wav")
            if segments is None:
                return None
        """
        try:
            # --- EXTERNAL CALL: faster-whisper / Whisper large-v3 ---
            segments, info = self.model.transcribe(
                audio_path,
                # beam_size=5 is the faster-whisper default — balances
                # accuracy and speed. Lower (e.g. 1) is faster but less accurate.
                beam_size=5,
            )
            # --- END EXTERNAL CALL ---
            return segments, info

        except Exception as e:
            self.logger.error(
                "Whisper transcription failed for '%s': %s\n"
                "Fix: Confirm the file is a valid 16kHz mono WAV. "
                "If the error persists, restart the pipeline.",
                audio_path,
                e,
            )
            return None, None
