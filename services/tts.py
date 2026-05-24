# ============================================================
# FILE: services/tts.py
#
# PURPOSE:
#   Converts Mandarin text to a spoken audio file and saves it to
#   TEMP_REPLY_AUDIO. The active backend is set by TTS_BACKEND in
#   config.py:
#     "kokoro" — Kokoro TTS library (Mac, CPU, no Docker)
#     "say"    — macOS built-in Mandarin voice via subprocess
#     "qwen3"  — Qwen3-TTS HTTP API (Brahma only, ROCm Docker)
#   If TTS_BACKEND = "kokoro" but the import fails (Python 3.13
#   blis/spacy incompatibility), the function falls back to "say"
#   automatically.
#
# INPUTS:
#   - mandarin_text (str): Mandarin Chinese text to synthesise
#
# OUTPUTS:
#   - audio_path (str): path to generated AIFF file ("say" backend)
#                       or other format depending on backend
#   - None: if all TTS backends fail
#
# DEPENDENCIES:
#   - subprocess (Python standard library) — for "say" backend
#   - kokoro (pip install kokoro) — optional, Mac only
#   - config.py → TTS_BACKEND, TTS_VOICE, TEMP_REPLY_AUDIO
#   - utils/logger.py
#
# CALLED BY:
#   - main.py → reply_pipeline()
#
# AUTHOR: Clip Project
# LAST UPDATED: 2026-05-30
# ============================================================

import subprocess
from pathlib import Path

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def generate_mandarin_audio(mandarin_text: str) -> str | None:
    """
    Converts Mandarin text to an audio file using the configured backend.

    Steps:
      1. Read TTS_BACKEND from config to select the engine.
      2a. "kokoro" — attempt Kokoro library synthesis; fall back to
          "say" automatically if Kokoro cannot be imported.
      2b. "say"    — synthesise via macOS built-in voice using subprocess.
      2c. "qwen3"  — not implemented for Mac (Brahma only); logs error.
      3. On success, return the output file path as a string.
         On failure, log the reason and return None.

    Args:
        mandarin_text (str): Mandarin Chinese text to speak.
                             Example: "我已经吃过了，谢谢。"

    Returns:
        str:  Path to the saved audio file. Example: "temp/reply.aiff"
        None: If all available backends fail or are unavailable.

    Example:
        path = generate_mandarin_audio("你好")
        if path:
            send_whatsapp_voice_note(path)
    """
    backend = config.TTS_BACKEND

    if backend == "kokoro":
        return _generate_with_kokoro(mandarin_text)

    if backend == "say":
        return _generate_with_say(mandarin_text)

    if backend == "qwen3":
        # Qwen3-TTS requires ROCm Docker — not available on Mac.
        # Switch TTS_BACKEND to "say" in config.py for Mac use.
        logger.error(
            "TTS_BACKEND = 'qwen3' is only supported on Brahma (ROCm).\n"
            "Fix: Set TTS_BACKEND = 'say' in config.py for Mac."
        )
        return None

    logger.error(
        "Unknown TTS_BACKEND value: '%s'\n"
        "Fix: Set TTS_BACKEND to 'kokoro', 'say', or 'qwen3' in config.py.",
        backend,
    )
    return None


def _generate_with_kokoro(mandarin_text: str) -> str | None:
    """
    Synthesises Mandarin audio using the Kokoro TTS library.

    Falls back to _generate_with_say() automatically if Kokoro is
    not installed — common on Python 3.13 due to blis/spacy wheel
    incompatibility.

    Steps:
      1. Import Kokoro — catch ImportError and fall back to "say".
      2. Initialise the Kokoro pipeline with the configured voice.
      3. Generate audio and save to TEMP_REPLY_AUDIO.
      4. Return the output path as a string.

    Args:
        mandarin_text (str): Mandarin text to synthesise.

    Returns:
        str:  Path to saved audio file on success.
        None: If Kokoro fails and "say" fallback also fails.

    Example:
        path = _generate_with_kokoro("你好")
    """
    try:
        # Kokoro may not be installable on Python 3.13 (blis C extension
        # has no arm64 wheel for 3.13 as of 2026-05). If the import fails,
        # fall back to the macOS "say" command rather than crashing.
        from kokoro import KPipeline
    except ImportError:
        logger.warning(
            "Kokoro is not available (likely Python 3.13 incompatibility).\n"
            "Falling back to macOS 'say' command."
        )
        return _generate_with_say(mandarin_text)

    try:
        logger.info("Generating audio with Kokoro (voice: %s)...", config.TTS_VOICE)

        # --- EXTERNAL CALL: Kokoro TTS ---
        pipeline = KPipeline(lang_code="z")
        generator = pipeline(mandarin_text, voice=config.TTS_VOICE)

        audio_segments = []
        for _, _, audio in generator:
            audio_segments.append(audio)
        # --- END EXTERNAL CALL ---

        if not audio_segments:
            logger.error(
                "Kokoro returned no audio segments.\n"
                "Fix: Check that the voice '%s' supports Mandarin input.",
                config.TTS_VOICE,
            )
            return None

        # Kokoro returns numpy float32 arrays — write as raw PCM then
        # encode. soundfile is installed as a Kokoro dependency.
        import numpy as np
        import soundfile as sf

        combined = np.concatenate(audio_segments)
        sf.write(str(config.TEMP_REPLY_AUDIO), combined, samplerate=24000)

        logger.info("Kokoro audio saved to %s", config.TEMP_REPLY_AUDIO)
        return str(config.TEMP_REPLY_AUDIO)

    except Exception as e:
        logger.error(
            "Kokoro synthesis failed: %s\n"
            "Fix: Reinstall Kokoro — pip install kokoro soundfile",
            e,
        )
        return None


def _generate_with_say(mandarin_text: str) -> str | None:
    """
    Synthesises Mandarin audio using the macOS built-in 'say' command.

    macOS ships a high-quality Mandarin neural voice called "Tingting"
    (System Preferences → Accessibility → Spoken Content → System Voice).
    The 'say' command can invoke it directly — no installation required.
    This makes it the most reliable Mac fallback for Python 3.13 where
    third-party TTS libraries may not have compatible wheels.

    Output format: AIFF. The 'say' command writes AIFF natively — no
    conversion needed. WhatsApp accepts AIFF voice notes on iPhone.
    TEMP_REPLY_AUDIO must use a .aiff extension for this backend.

    Steps:
      1. Build the subprocess command using TTS_VOICE from config.
      2. Run 'say' with -v (voice), -o (output file), and the text.
      3. Check the return code — non-zero means 'say' failed.
      4. Return the output file path as a string on success.

    Args:
        mandarin_text (str): Mandarin text to synthesise.

    Returns:
        str:  Path to saved AIFF file on success.
        None: If the 'say' command fails or is unavailable.

    Example:
        path = _generate_with_say("你好")
    """
    output_path = str(config.TEMP_REPLY_AUDIO)

    # TTS_VOICE must exactly match the macOS voice name.
    # "Tingting" works; "Ting-Ting" (with hyphen) fails silently.
    # To list all installed voices: say -v '?'
    command = ["say", "-v", config.TTS_VOICE, "-o", output_path, mandarin_text]

    logger.info(
        "Generating audio with macOS 'say' (voice: %s)...", config.TTS_VOICE
    )

    try:
        # --- EXTERNAL CALL: macOS say command ---
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        # --- END EXTERNAL CALL ---

    except FileNotFoundError:
        logger.error(
            "'say' command not found.\n"
            "Fix: This backend requires macOS. Use TTS_BACKEND = 'qwen3' on Linux."
        )
        return None

    if result.returncode != 0:
        logger.error(
            "'say' command failed (exit %d): %s\n"
            "Fix: Confirm voice '%s' is installed — run: say -v '?' | grep -i mandarin",
            result.returncode,
            result.stderr.strip(),
            config.TTS_VOICE,
        )
        return None

    logger.info("'say' audio saved to %s", output_path)
    return output_path
