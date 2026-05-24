# ============================================================
# FILE: services/bot.py
#
# PURPOSE:
#   Telegram Bot interface for LingoBridge. Replaces the keyboard-
#   driven main.py loop with a chat-based interface so the owner
#   can receive Mandarin → English translations and send English
#   → Mandarin voice replies, all from their phone.
#
#   Two conversation flows:
#     FORWARD — owner (or MIL via owner's phone) sends a Mandarin
#               voice message → bot replies with the English text
#               plus the original Mandarin transcript.
#     REPLY   — owner taps "Reply in Mandarin" or sends /reply →
#               bot asks for an English voice message → generates
#               Mandarin audio → sends back as a voice note.
#
# INPUTS:
#   - Telegram voice messages (.ogg format) from the bot user
#   - /start, /begin, /end, /reply, /help, /stop commands
#   - Inline button presses (Reply in Mandarin, Try again)
#
# OUTPUTS:
#   - Text messages with transcript + translation
#   - Audio messages (Mandarin audio as .m4a file)
#   - Inline keyboards for quick actions
#
# DEPENDENCIES:
#   - python-telegram-bot (pip install python-telegram-bot)
#   - services/transcribe.py → Transcriber class
#   - services/translate.py  → translate_to_english, translate_to_mandarin
#   - services/tts.py        → generate_mandarin_audio
#   - config.py → TELEGRAM_BOT_TOKEN, TEMP_INPUT_AUDIO, TEMP_REPLY_AUDIO
#   - utils/logger.py
#
# CALLED BY:
#   - Run directly: python services/bot.py
#
# AUTHOR: Clip Project
# LAST UPDATED: 2026-05-25 (rev 6)
# ============================================================

import subprocess
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from services.transcribe import Transcriber
from services.translate import translate_to_english, translate_to_mandarin
from services.tts import generate_mandarin_audio
from utils.logger import get_logger

logger = get_logger(__name__)


# ── Manual state tracking ─────────────────────────────────────
# Manual state tracking per chat_id. Replaces PTB ConversationHandler
# which cannot mix MessageHandler and CallbackQueryHandler in the same
# state without the per_message warning. Dict is keyed by chat_id to
# support multiple users if needed in future.
_user_states: dict[int, str] = {}

# Valid states
IDLE              = "idle"               # session not started
WAITING_FOR_MIL   = "waiting_for_mil"    # listening for Mandarin voice
WAITING_FOR_REPLY = "waiting_for_reply"  # waiting for English voice reply


# ── Module-level Transcriber singleton ───────────────────────
# Loaded once at startup — avoids 3-5 second reload per cycle.
_transcriber: Transcriber | None = None


def _get_transcriber() -> Transcriber:
    """
    Returns the module-level Transcriber singleton, creating it if needed.

    Steps:
      1. Check if _transcriber is already initialised.
      2. If not, create a new Transcriber (loads Whisper model).
      3. Return the singleton.

    Args:
        None

    Returns:
        Transcriber: The loaded Whisper model wrapper.

    Example:
        t = _get_transcriber()
        result = t.transcribe_audio("temp/input.ogg")
    """
    global _transcriber
    if _transcriber is None:
        logger.info("Initialising Whisper Transcriber...")
        _transcriber = Transcriber()
    return _transcriber


# ── Command handlers ──────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles /start — greets the user and explains how to begin.

    Does not start a session. The owner must send /begin to activate
    listening. This keeps the welcome message visible without
    immediately changing state.

    Steps:
      1. Log the user.
      2. Send a welcome message pointing to /begin.

    Args:
        update (Update): Incoming Telegram update.
        context (ContextTypes.DEFAULT_TYPE): Handler context.

    Returns:
        None

    Example:
        Triggered when user sends /start in the bot chat.
    """
    logger.info("Bot started by user %s", update.effective_user.id)

    await update.message.reply_text(
        "🌉 LingoBridge is ready.\n"
        "Type /begin to start listening for Mandarin.\n"
        "Or type /help to see all commands."
    )


async def cmd_begin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles /begin — starts a session and sets state to WAITING_FOR_MIL.

    Steps:
      1. Set _user_states[chat_id] = WAITING_FOR_MIL.
      2. Tell the owner to send a Mandarin voice message.

    Args:
        update (Update): Incoming Telegram update.
        context (ContextTypes.DEFAULT_TYPE): Handler context.

    Returns:
        None

    Example:
        User sends /begin → bot sets state to WAITING_FOR_MIL.
    """
    chat_id = update.effective_chat.id
    _user_states[chat_id] = WAITING_FOR_MIL

    logger.info("Session started for chat %s → %s", chat_id, WAITING_FOR_MIL)

    await update.message.reply_text(
        "🎙 Listening for Mandarin. Send a voice message to translate."
    )


async def cmd_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles /end — ends the session and resets state to IDLE.

    Steps:
      1. Set _user_states[chat_id] = IDLE.
      2. Delete any leftover temp audio files (privacy).
      3. Confirm to the owner that the session has ended.

    Args:
        update (Update): Incoming Telegram update.
        context (ContextTypes.DEFAULT_TYPE): Handler context.

    Returns:
        None

    Example:
        User sends /end → bot clears state and deletes temp files.
    """
    chat_id = update.effective_chat.id
    _user_states[chat_id] = IDLE

    logger.info("Session ended for chat %s → %s", chat_id, IDLE)

    # Clear any leftover temp files from the previous session.
    _delete_temp_file(str(config.TEMP_INPUT_AUDIO.with_suffix(".ogg")))
    _delete_temp_file(str(config.TEMP_REPLY_AUDIO))
    _delete_temp_file(str(config.TEMP_REPLY_M4A))

    await update.message.reply_text(
        "⏹ Session ended. Type /begin to start a new session."
    )


async def cmd_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles /reply — switches state to WAITING_FOR_REPLY.

    Steps:
      1. Check state — if IDLE, prompt user to /begin first.
      2. Set _user_states[chat_id] = WAITING_FOR_REPLY.
      3. Prompt owner to send an English voice message.

    Args:
        update (Update): Incoming Telegram update.
        context (ContextTypes.DEFAULT_TYPE): Handler context.

    Returns:
        None

    Example:
        User sends /reply → bot sets state to WAITING_FOR_REPLY.
    """
    chat_id = update.effective_chat.id

    if _user_states.get(chat_id, IDLE) == IDLE:
        await update.message.reply_text(
            "⚠️ No active session. Type /begin to start."
        )
        return

    _user_states[chat_id] = WAITING_FOR_REPLY
    logger.info("Reply mode for chat %s → %s", chat_id, WAITING_FOR_REPLY)

    await update.message.reply_text(
        "🎙 Send a voice message with your English reply."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles /help — displays all available commands.

    Steps:
      1. Send the help text listing every command.

    Args:
        update (Update): Incoming Telegram update.
        context (ContextTypes.DEFAULT_TYPE): Handler context.

    Returns:
        None

    Example:
        Triggered when user sends /help.
    """
    await update.message.reply_text(
        "Commands:\n"
        "/begin → start listening for Mandarin\n"
        "/end   → end the session\n"
        "🎙 Send voice message → translates Mandarin to English\n"
        "/reply → send your English reply in Mandarin\n"
        "/stop  → stop the bot\n"
        "/help  → show this message"
    )


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles /stop — clears state and sends a goodbye message.

    Steps:
      1. Set _user_states[chat_id] = IDLE.
      2. Send a goodbye message.

    Args:
        update (Update): Incoming Telegram update.
        context (ContextTypes.DEFAULT_TYPE): Handler context.

    Returns:
        None

    Example:
        Triggered when user sends /stop.
    """
    chat_id = update.effective_chat.id
    _user_states[chat_id] = IDLE

    logger.info("Bot stopped by user %s", update.effective_user.id)
    await update.message.reply_text("LingoBridge stopped.")


# ── Voice message dispatcher ──────────────────────────────────

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Routes incoming voice messages based on the user's current state.

    Steps:
      1. Read state from _user_states for this chat_id.
      2. IDLE           → reply "No active session. Type /begin to start."
      3. WAITING_FOR_MIL   → run the forward pipeline (Mandarin → English).
      4. WAITING_FOR_REPLY → run the reverse pipeline (English → Mandarin).
      5. Any other value   → ignore silently.

    Args:
        update (Update): Incoming Telegram update containing a voice message.
        context (ContextTypes.DEFAULT_TYPE): Handler context.

    Returns:
        None

    Example:
        User sends voice → handler checks state and routes accordingly.
    """
    chat_id = update.effective_chat.id
    state = _user_states.get(chat_id, IDLE)

    if state == IDLE:
        await update.message.reply_text(
            "⚠️ No active session. Type /begin to start."
        )
        return

    if state == WAITING_FOR_MIL:
        await _run_forward_pipeline(update, context)
        return

    if state == WAITING_FOR_REPLY:
        await _run_reverse_pipeline(update, context)
        return


# ── Inline button handlers ────────────────────────────────────

async def handle_button_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the "Reply in Mandarin" inline button.

    Steps:
      1. Acknowledge the callback query (removes Telegram loading spinner).
      2. Set state to WAITING_FOR_REPLY.
      3. Prompt owner to send an English voice message.

    Args:
        update (Update): Incoming Telegram update (callback query).
        context (ContextTypes.DEFAULT_TYPE): Handler context.

    Returns:
        None

    Example:
        User taps "Reply in Mandarin" button → state set to WAITING_FOR_REPLY.
    """
    query = update.callback_query
    chat_id = update.effective_chat.id

    try:
        await query.answer()
    except Exception as e:
        logger.warning("Could not acknowledge callback query: %s", e)

    _user_states[chat_id] = WAITING_FOR_REPLY
    logger.info("Reply button → chat %s set to %s", chat_id, WAITING_FOR_REPLY)

    await query.message.reply_text(
        "🎙 Send a voice message with your English reply."
    )


async def handle_button_try_again(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the "Try again" inline button.

    Steps:
      1. Acknowledge the callback query.
      2. Delete the last bot message so the chat stays clean.
      3. Set state to WAITING_FOR_MIL.
      4. Prompt the user to send another voice message.

    Args:
        update (Update): Incoming Telegram update (callback query).
        context (ContextTypes.DEFAULT_TYPE): Handler context.

    Returns:
        None

    Example:
        User taps "Try again" → state stays WAITING_FOR_MIL, re-prompts.
    """
    query = update.callback_query
    chat_id = update.effective_chat.id

    try:
        await query.answer()
        await query.message.delete()
    except Exception as e:
        logger.warning("Could not delete message on try_again: %s", e)

    _user_states[chat_id] = WAITING_FOR_MIL
    logger.info("Try again button → chat %s set to %s", chat_id, WAITING_FOR_MIL)

    await query.message.chat.send_message(
        "🎙 Send another voice message — listening for Mandarin."
    )


# ── Pipeline implementations ──────────────────────────────────

async def _run_forward_pipeline(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Forward pipeline: Mandarin voice → English text sent to owner.

    Steps:
      1. Download the .ogg voice file from Telegram to temp/input.ogg.
      2. Transcribe with Whisper — returns None if not Mandarin.
      3. If None → reply "No Mandarin detected". State stays WAITING_FOR_MIL.
      4. Translate Mandarin → English via Ollama.
      5. If None → reply "Translation failed". State stays WAITING_FOR_MIL.
      6. Send transcript + translation text to the owner.
      7. Attach inline buttons: [Reply in Mandarin] and [Try again].
      8. Delete temp audio file (privacy).

    Args:
        update (Update): Incoming Telegram update containing a voice message.
        context (ContextTypes.DEFAULT_TYPE): Handler context.

    Returns:
        None

    Example:
        User sends Mandarin voice → bot replies with English translation.
    """
    ogg_path = str(config.TEMP_INPUT_AUDIO.with_suffix(".ogg"))

    # Step 1: Download the voice file from Telegram.
    downloaded = await _download_voice(update, ogg_path)
    if not downloaded:
        return

    # Step 2: Transcribe — faster-whisper accepts .ogg natively.
    logger.info("Transcribing Mandarin voice from %s...", ogg_path)
    transcript = _get_transcriber().transcribe_audio(ogg_path)

    _delete_temp_file(ogg_path)

    # Step 3: Reject if not Mandarin.
    if transcript is None:
        await update.message.reply_text("⚠️ No Mandarin detected. Try again.")
        return

    # Step 4: Translate Mandarin → English.
    logger.info("Translating to English: %s", transcript)
    english = translate_to_english(transcript)

    if english is None:
        await update.message.reply_text("⚠️ Translation failed. Try again.")
        return

    # Step 6: Build and send the reply with both languages.
    reply_text = (
        "她说 (She said):\n"
        f"🇨🇳 {transcript}\n"
        f"🇬🇧 {english}"
    )

    # callback_data "reply_button" matches the CallbackQueryHandler pattern.
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Reply in Mandarin", callback_data="reply_button"),
            InlineKeyboardButton("🔄 Try again",         callback_data="try_again"),
        ]
    ])

    try:
        await update.message.reply_text(reply_text, reply_markup=keyboard)
    except Exception as e:
        logger.error(
            "Failed to send translation reply: %s\n"
            "Fix: Check Telegram bot token and network connectivity.",
            e,
        )


async def _run_reverse_pipeline(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Reverse pipeline: English voice → Mandarin audio sent to owner.

    Steps:
      1. Download .ogg voice file to temp/input.ogg.
      2. Transcribe English speech (no language filter).
      3. If None → reply error. State stays WAITING_FOR_REPLY.
      3b. Reject if confidence < 0.4 or language not in ("en", "zh").
          State stays WAITING_FOR_REPLY so owner can try again.
      4. Translate English → Mandarin via Ollama.
      5. If None → reply error. State stays WAITING_FOR_REPLY.
      6. Generate Mandarin TTS audio (.aiff on Mac).
      7. If None → send text only. Reset state to WAITING_FOR_MIL.
      8. Convert .aiff → .m4a via afconvert.
      9. If m4a returned → send_audio() + text with Mandarin. Reset state.
      10. If conversion failed → send text only. Reset state.
      11. Delete all temp audio files (privacy).

    Args:
        update (Update): Incoming Telegram update containing a voice message.
        context (ContextTypes.DEFAULT_TYPE): Handler context.

    Returns:
        None

    Example:
        Owner sends English voice note → bot sends Mandarin audio back.
    """
    chat_id = update.effective_chat.id
    ogg_path = str(config.TEMP_INPUT_AUDIO.with_suffix(".ogg"))

    # Step 1: Download the English voice file.
    downloaded = await _download_voice(update, ogg_path)
    if not downloaded:
        return

    # Step 2: Transcribe — no Mandarin filter, owner is speaking English.
    logger.info("Transcribing English reply from %s...", ogg_path)
    transcription_result = _transcribe_any_language(ogg_path)

    _delete_temp_file(ogg_path)

    if transcription_result is None:
        await update.message.reply_text(
            "⚠️ Could not transcribe your voice. Please try again."
        )
        return

    english_text, detected_language, confidence = transcription_result

    # Step 3b: Reject if confidence too low or language is not English.
    # Prevents noise or wrong-language audio from reaching the translation
    # step and producing a garbled or nonsensical Mandarin reply.
    if confidence < 0.4 or detected_language not in ("en", "zh"):
        logger.info(
            "Rejected reply — language=%s confidence=%.2f",
            detected_language,
            confidence,
        )
        await update.message.reply_text(
            "⚠️ Could not understand your reply clearly.\n"
            "Please speak slowly in English and try again."
        )
        _user_states[chat_id] = WAITING_FOR_REPLY
        return

    # Step 4: Translate English → Mandarin.
    logger.info("Translating to Mandarin: %s", english_text)
    mandarin_text = translate_to_mandarin(english_text)

    if mandarin_text is None:
        await update.message.reply_text("⚠️ Translation failed. Try again.")
        return

    # Step 6: Generate Mandarin TTS audio (.aiff on Mac).
    logger.info("Generating Mandarin audio...")
    aiff_path = generate_mandarin_audio(mandarin_text)

    reply_text = (
        "Your reply in Mandarin:\n"
        f"🇨🇳 {mandarin_text}\n"
        "👆 Play this to MIL"
    )

    if aiff_path is None:
        logger.warning("TTS failed — sending Mandarin text only.")
        await update.message.reply_text(
            "⚠️ Audio generation failed. Mandarin text only:\n\n" + reply_text
        )
        _user_states[chat_id] = WAITING_FOR_MIL
        return

    # Step 8: Convert .aiff → .m4a for Telegram.
    # send_audio() accepts M4A/AAC natively. OGG/OPUS and MP3 are not
    # supported by afconvert on macOS Tahoe, so M4A is the correct target.
    m4a_path = _convert_aiff_to_m4a(aiff_path)

    # Step 9–10: Send audio + text, or text only if conversion failed.
    if m4a_path is not None:
        await _send_audio_reply(update, context, str(m4a_path))
        await update.message.reply_text(reply_text)
        _delete_temp_file(str(m4a_path))
    else:
        logger.warning("M4A conversion failed — sending Mandarin text only.")
        await update.message.reply_text(
            "🔊 Audio conversion failed — text only:\n\n" + reply_text
        )

    # Step 11: Clean up original .aiff and reset state.
    _delete_temp_file(aiff_path)
    _user_states[chat_id] = WAITING_FOR_MIL
    logger.info("Reverse pipeline complete — chat %s reset to %s", chat_id, WAITING_FOR_MIL)


# ── Internal helpers ──────────────────────────────────────────

def _convert_aiff_to_m4a(aiff_path: str) -> Path | None:
    """
    Converts an AIFF file to M4A/AAC using macOS afconvert.

    Telegram's send_audio() accepts M4A/AAC natively. The macOS 'say'
    TTS backend writes AIFF — this conversion makes the file playable
    in Telegram. OGG/OPUS and MP3 encoding are not supported by
    afconvert on macOS Tahoe, so M4A/AAC is the correct target format.

    Steps:
      1. Define m4a_path as temp/reply.m4a.
      2. Run afconvert with format m4af and codec aac via subprocess.
      3. Return m4a_path on success.
      4. On CalledProcessError → log error and return None so the
         caller can fall back to sending text only.

    Args:
        aiff_path (str): Path to the source AIFF file (e.g. "temp/reply.aiff").

    Returns:
        Path: Path to the converted M4A file on success.
        None: If afconvert fails or is unavailable.

    Example:
        m4a = _convert_aiff_to_m4a("temp/reply.aiff")
        if m4a:
            await context.bot.send_audio(chat_id=chat_id, audio=open(m4a, "rb"))
    """
    m4a_path = Path("temp") / "reply.m4a"

    logger.info("Converting %s → %s via afconvert...", aiff_path, m4a_path)

    try:
        # --- EXTERNAL CALL: macOS afconvert ---
        subprocess.run(
            [
                "/usr/bin/afconvert",
                "-f", "m4af",
                "-d", "aac",
                str(aiff_path),
                str(m4a_path),
            ],
            capture_output=True,
            check=True,
        )
        # --- END EXTERNAL CALL ---
        logger.info("Conversion successful: %s", m4a_path)
        return m4a_path

    except subprocess.CalledProcessError as e:
        logger.error(
            "afconvert m4a conversion failed (exit %d): %s\n"
            "Fix: afconvert m4a conversion failed — sending text only",
            e.returncode,
            e.stderr.decode(errors="replace").strip(),
        )
        return None


async def _download_voice(update: Update, dest_path: str) -> bool:
    """
    Downloads a Telegram voice message (.ogg) to the given file path.

    3 retries with 2s delay handles transient network issues on
    high-latency ISP routing (Singapore → Europe → Telegram).
    Fails cleanly after 3 attempts with a clear error.

    Steps:
      1. Attempt up to 3 times to get the File object and download it.
      2. On success, log and return True immediately (break the loop).
      3. On failure with attempts remaining, log a warning and wait 2s.
      4. On failure after all 3 attempts, log an error and return False.

    Args:
        update (Update): Telegram update containing a voice message.
        dest_path (str): Local path to save the .ogg file.

    Returns:
        bool: True if file downloaded successfully, False after 3 failures.

    Example:
        ok = await _download_voice(update, "temp/input.ogg")
    """
    import asyncio

    for attempt in range(3):
        try:
            # --- EXTERNAL CALL: Telegram Bot API — getFile + download ---
            voice_file = await update.message.voice.get_file()
            await voice_file.download_to_drive(dest_path)
            # --- END EXTERNAL CALL ---
            logger.info("Voice file downloaded to %s", dest_path)
            return True

        except Exception as e:
            if attempt < 2:
                logger.warning(
                    "Download attempt %d failed: %s. Retrying in 2 seconds...",
                    attempt + 1,
                    e,
                )
                await asyncio.sleep(2)
            else:
                logger.error(
                    "Failed to download voice message after 3 attempts: %s\n"
                    "Fix: Check internet connection to api.telegram.org",
                    e,
                )
                try:
                    await update.message.reply_text(
                        "⚠️ Could not download your voice message. Please try again."
                    )
                except Exception:
                    pass

    return False


def _transcribe_any_language(
    audio_path: str,
) -> tuple[str, str, float] | None:
    """
    Transcribes audio without the Mandarin language filter.

    The standard Transcriber.transcribe_audio() rejects non-Mandarin audio.
    For the reply flow the owner speaks English, so we need to accept any
    language. This function calls the internal Whisper model directly and
    returns the transcript together with language metadata so the caller
    can apply its own confidence and language checks.

    Steps:
      1. Get the Transcriber singleton.
      2. Verify model is loaded.
      3. Call _run_whisper() to get raw Whisper output.
      4. Collect all segment texts and join into one string.
      5. Return (transcript, detected_language, confidence) as a tuple.

    Args:
        audio_path (str): Path to the voice file (WAV or .ogg).

    Returns:
        tuple[str, str, float]: (transcript_text, detected_language, confidence)
            Example: ("Yes I already ate", "en", 0.97)
        None: If the model is not loaded, the file is missing, Whisper
              fails, or the transcript is empty.

    Example:
        result = _transcribe_any_language("temp/input.ogg")
        if result is None:
            return
        transcript, language, confidence = result
    """
    transcriber = _get_transcriber()

    if transcriber.model is None:
        logger.error(
            "Whisper model not loaded — cannot transcribe English reply.\n"
            "Fix: Check the startup error and restart the bot."
        )
        return None

    if not Path(audio_path).exists():
        logger.error(
            "Audio file not found: %s\n"
            "Fix: Check that the voice download step completed successfully.",
            audio_path,
        )
        return None

    segments, info = transcriber._run_whisper(audio_path)
    if segments is None:
        return None

    logger.info(
        "Detected language: %s (confidence: %.2f)",
        info.language,
        info.language_probability,
    )

    transcript = " ".join(segment.text.strip() for segment in segments)

    if not transcript.strip():
        logger.info("Transcript is empty after joining segments — skipping.")
        return None

    logger.info("Transcript: %s", transcript)
    return transcript, info.language, info.language_probability


async def _send_audio_reply(
    update: Update, context: ContextTypes.DEFAULT_TYPE, audio_path: str
) -> None:
    """
    Sends a local M4A file as a Telegram audio message.

    Uses send_audio() rather than send_voice() because Telegram accepts
    M4A/AAC via send_audio() natively. send_voice() requires Opus OGG,
    which afconvert cannot produce on macOS Tahoe.

    Steps:
      1. Open the M4A file from disk.
      2. Send it via context.bot.send_audio() to the current chat.
      3. Log success or error.

    Args:
        update (Update): Telegram update (used to get chat_id).
        context (ContextTypes.DEFAULT_TYPE): Handler context (provides bot).
        audio_path (str): Path to the local M4A file (e.g. "temp/reply.m4a").

    Returns:
        None

    Example:
        await _send_audio_reply(update, context, "temp/reply.m4a")
    """
    chat_id = update.effective_chat.id

    try:
        with open(audio_path, "rb") as audio_file:
            # --- EXTERNAL CALL: Telegram Bot API — sendAudio ---
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=audio_file,
            )
            # --- END EXTERNAL CALL ---
        logger.info("Mandarin audio sent to chat %s", chat_id)

    except Exception as e:
        logger.error(
            "Failed to send audio: %s\n"
            "Fix: Confirm the M4A file at '%s' is valid and the bot "
            "has permission to send audio messages.",
            e,
            audio_path,
        )
        try:
            await update.message.reply_text(
                "⚠️ Could not send the audio file. Mandarin text sent above."
            )
        except Exception:
            pass


def _delete_temp_file(file_path: str) -> None:
    """
    Deletes a temp file if it exists. Logs a warning on failure.

    Temp files are always deleted after each pipeline cycle to protect
    privacy — no audio data persists between conversations.

    Steps:
      1. Resolve path.
      2. Delete if exists.
      3. Log warning on any OS error (non-fatal).

    Args:
        file_path (str): Path to the file to delete.

    Returns:
        None

    Example:
        _delete_temp_file("temp/input.ogg")
    """
    path = Path(file_path)
    try:
        if path.exists():
            path.unlink()
            logger.debug("Deleted temp file: %s", file_path)
    except OSError as e:
        logger.warning(
            "Could not delete temp file '%s': %s\n"
            "Fix: Check file permissions in the temp/ directory.",
            file_path,
            e,
        )


# ── Bot setup and entry point ─────────────────────────────────

def build_application() -> Application:
    """
    Builds and configures the Telegram Application with all handlers.

    Uses standalone handlers and manual state tracking instead of
    ConversationHandler — avoids the PTBUserWarning that fires when
    CallbackQueryHandlers and MessageHandlers share a state.

    Steps:
      1. Validate TELEGRAM_BOT_TOKEN is set.
      2. Create the Application via the builder pattern.
      3. Register CommandHandlers for all commands.
      4. Register a single MessageHandler (voice) that dispatches by state.
      5. Register CallbackQueryHandlers for inline buttons.
      6. Return the configured application.

    Args:
        None

    Returns:
        Application: Configured Telegram application ready to run.

    Raises:
        SystemExit: If TELEGRAM_BOT_TOKEN is not set in .env.

    Example:
        app = build_application()
        app.run_polling()
    """
    token = config.TELEGRAM_BOT_TOKEN

    if not token:
        logger.critical(
            "TELEGRAM_BOT_TOKEN is not set.\n"
            "Fix: Add TELEGRAM_BOT_TOKEN=your_token to your .env file. "
            "Get a token from @BotFather on Telegram."
        )
        raise SystemExit(1)

    # Never log the token value — log only that it was loaded.
    logger.info("Telegram bot token loaded successfully.")

    # Extended timeouts needed for voice file downloads over high-latency
    # connections (175ms+ to api.telegram.org). Default read timeout causes
    # 'Timed out' errors on voice message downloads despite good connectivity.
    # read_timeout=60 covers large voice files on slow links.
    # get_updates_read_timeout=60 prevents polling disconnects.

    # --- EXTERNAL CALL: python-telegram-bot Application builder ---
    app = (
        Application.builder()
        .token(token)
        .connect_timeout(30)
        .read_timeout(60)
        .write_timeout(30)
        .get_updates_read_timeout(60)
        .build()
    )
    # --- END EXTERNAL CALL ---

    # Command handlers — each is independent, no ConversationHandler needed.
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("begin", cmd_begin))
    app.add_handler(CommandHandler("end",   cmd_end))
    app.add_handler(CommandHandler("reply", cmd_reply))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CommandHandler("stop",  cmd_stop))

    # Single voice handler — routes to forward or reverse pipeline by state.
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Inline button handlers — pattern matches callback_data strings.
    app.add_handler(CallbackQueryHandler(handle_button_reply,     pattern="^reply_button$"))
    app.add_handler(CallbackQueryHandler(handle_button_try_again, pattern="^try_again$"))

    return app


if __name__ == "__main__":
    logger.info("LingoBridge bot started — waiting for messages...")
    application = build_application()
    application.run_polling()
