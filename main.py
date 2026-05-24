# ============================================================
# FILE: main.py
#
# PURPOSE:
#   Entry point for LingoBridge. Runs the pipeline loop in forward
#   mode by default (listening for MIL's Mandarin speech) and
#   switches to reply mode when R is pressed. Contains no business
#   logic — all work is delegated to services/.
#
# INPUTS:
#   - Keyboard: R key (reply mode for one cycle), Q key (quit)
#   - Microphone audio (via services/audio_capture.py)
#
# OUTPUTS:
#   - WhatsApp text message (forward mode: English translation)
#   - WhatsApp Mandarin text + local AIFF playback (reply mode)
#
# DEPENDENCIES:
#   - pynput (pip install pynput) — non-blocking keyboard listener
#   - services/audio_capture.py, transcribe.py, translate.py,
#     tts.py, whatsapp.py
#   - utils/logger.py
#   - config.py
#
# CALLED BY:
#   - User via: python main.py
#
# AUTHOR: Clip Project
# LAST UPDATED: 2026-05-31
# ============================================================

import subprocess
from pathlib import Path

from pynput import keyboard

import config
from services.audio_capture import AudioCapture
from services.transcribe import Transcriber
from services.translate import translate_to_english, translate_to_mandarin
from services.tts import generate_mandarin_audio
from services.whatsapp import send_mandarin_text, send_text_message
from utils.logger import get_logger

logger = get_logger(__name__)

# Shared service instances — initialised once at startup so the
# Whisper model is loaded into RAM before the first recording begins.
_capture    = AudioCapture()
_transcriber = Transcriber()

# Flag set by the keyboard listener when the owner presses R.
# The main loop checks this flag at the start of each cycle and
# runs reply_pipeline() instead of forward_pipeline() when True.
_reply_requested = False

# Flag set by Q key to break the main loop gracefully.
_quit_requested = False


def _delete_audio(path: str | None) -> None:
    """
    Deletes a temporary audio file from disk.

    Audio files are deleted after every pipeline cycle — never stored.
    This is a hard privacy requirement: conversation audio between
    family members must not accumulate on disk. Each cycle produces
    one recording; it is deleted as soon as the pipeline is done with it.

    Steps:
      1. Return immediately if path is None (nothing to delete).
      2. Resolve the path and delete if it exists.
      3. Log a warning if deletion fails (non-fatal — pipeline continues).

    Args:
        path (str | None): File path to delete, or None to skip.

    Returns:
        None
    """
    if path is None:
        return
    try:
        Path(path).unlink(missing_ok=True)
    except OSError as e:
        logger.warning("Could not delete audio file '%s': %s", path, e)


def forward_pipeline() -> None:
    """
    Runs one forward-mode cycle: capture → transcribe → translate → send.

    Called continuously from the main loop while the owner is not
    actively replying. Listens for MIL's Mandarin speech, translates
    it to English, and sends it to the owner's WhatsApp as a text.

    Steps:
      1. Record mic until silence is detected.
      2. Skip cycle if no audio was captured.
      3. Transcribe audio — returns None if language is not Mandarin.
      4. Skip and clean up if transcript is None.
      5. Translate Mandarin transcript to English.
      6. Skip and clean up if translation failed.
      7. Send English text to owner's WhatsApp.
      8. Delete audio file (privacy — see _delete_audio).

    Args:
        None

    Returns:
        None
    """
    audio_path = _capture.capture_audio()

    if audio_path is None:
        return

    transcript = _transcriber.transcribe_audio(audio_path)

    if transcript is None:
        _delete_audio(audio_path)
        return

    english = translate_to_english(transcript)

    if english is None:
        _delete_audio(audio_path)
        return

    send_text_message(english)
    print(f"[FORWARD] Heard: {transcript} → {english}")

    # Audio deleted here — not earlier — so it is available for the
    # full pipeline. Never kept beyond the cycle that produced it.
    _delete_audio(audio_path)


def reply_pipeline() -> None:
    """
    Runs one reply-mode cycle: capture → transcribe → translate → send + play.

    Triggered when the owner presses R. Records the owner's English
    reply, translates it to Mandarin, sends it as a WhatsApp text so
    the owner can show the screen to MIL, and plays the Mandarin audio
    aloud via the Mac speaker so MIL can hear it directly.

    Steps:
      1. Print prompt so owner knows recording has started.
      2. Record owner's English speech.
      3. Skip if no audio captured.
      4. Transcribe English speech to text.
      5. Translate English to Mandarin.
      6. Send Mandarin as WhatsApp text (Phase 1: owner shows screen).
      7. Generate Mandarin audio with TTS.
      8. Play audio locally via afplay so MIL hears it in the room.
      9. Delete all temp audio files.

    Args:
        None

    Returns:
        None
    """
    print("[REPLY]   Recording your English reply...")

    audio_path = _capture.capture_audio()

    if audio_path is None:
        return

    english = _transcriber.transcribe_audio(audio_path)

    if english is None:
        _delete_audio(audio_path)
        return

    mandarin = translate_to_mandarin(english)

    if mandarin is None:
        _delete_audio(audio_path)
        return

    # Send as text first — Phase 1 fallback so owner can show screen
    # to MIL while voice note delivery via public URL is not yet set up.
    send_mandarin_text(mandarin)

    # Generate and play Mandarin audio locally so MIL hears the reply
    # spoken aloud in the room — no phone needed on MIL's side.
    reply_audio_path = generate_mandarin_audio(mandarin)

    if reply_audio_path is not None:
        # afplay is macOS built-in — plays AIFF/WAV/MP3 to system speaker.
        # Non-blocking enough for our use: we wait for playback to finish
        # before resuming the loop, which is correct (MIL must hear it fully).
        subprocess.run(["afplay", reply_audio_path], check=False)

    print("[REPLY]   Mandarin sent to WhatsApp + played aloud.")

    _delete_audio(audio_path)
    _delete_audio(reply_audio_path)


def _on_key_press(key: keyboard.Key) -> None:
    """
    Handles a single keypress from the pynput listener.

    Sets module-level flags read by the main loop. The listener runs
    in its own thread — flags are the safest way to communicate back
    to the main thread without locks or queues.

    Args:
        key: pynput Key or KeyCode object for the pressed key.

    Returns:
        None
    """
    global _reply_requested, _quit_requested

    try:
        char = key.char.lower() if hasattr(key, "char") and key.char else None
    except AttributeError:
        return

    if char == "r":
        _reply_requested = True
    elif char == "q":
        _quit_requested = True


def main() -> None:
    """
    Starts the LingoBridge pipeline loop.

    Prints the startup banner, launches the keyboard listener, then
    runs the forward/reply pipeline in a continuous loop until Q is
    pressed or Ctrl+C is received.

    # pynput.keyboard.Listener is used instead of input() or getch()
    # because it is non-blocking — it runs in a background thread and
    # does not interrupt or pause the mic capture loop. input() would
    # block the entire thread, making it impossible to listen for speech
    # and key presses at the same time.

    Args:
        None

    Returns:
        None
    """
    global _reply_requested, _quit_requested

    print("================================")
    print(" LingoBridge v0.1.0 — Running  ")
    print("================================")
    print("Listening for Mandarin...")
    print("Controls: R = reply | Q = quit")

    # pynput listener runs in a daemon thread — it fires _on_key_press
    # for every key event without blocking the main pipeline loop.
    listener = keyboard.Listener(on_press=_on_key_press)
    listener.start()

    try:
        while not _quit_requested:
            if _reply_requested:
                _reply_requested = False
                reply_pipeline()
            else:
                forward_pipeline()

    except KeyboardInterrupt:
        # Ctrl+C is a normal way to stop the process during development.
        pass

    finally:
        listener.stop()
        print("LingoBridge stopped.")


if __name__ == "__main__":
    main()
