# ============================================================
# FILE: services/whatsapp.py
#
# PURPOSE:
#   Sends messages to the owner's WhatsApp via the Twilio API.
#   Two message types:
#     - Text message  (forward mode: English translation of MIL's speech)
#     - Voice note    (reply mode: Mandarin AIFF audio for MIL to hear)
#   Credentials are read from config.py which loads them from .env.
#   This file never reads .env directly and never logs credential values.
#
# INPUTS:
#   - message    (str): English text to send as a WhatsApp message
#   - audio_path (str): path to AIFF voice note to send as media
#
# OUTPUTS:
#   - bool: True if Twilio accepted the message, False on any failure
#
# DEPENDENCIES:
#   - twilio (pip install twilio)
#   - config.py → TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
#                 TWILIO_WHATSAPP_FROM, MY_WHATSAPP_NUMBER
#   - utils/logger.py
#
# CALLED BY:
#   - main.py → forward_pipeline(), reply_pipeline()
#
# AUTHOR: Clip Project
# LAST UPDATED: 2026-05-31
# ============================================================

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def send_text_message(message: str) -> bool:
    """
    Sends an English text message to the owner's WhatsApp number.

    Steps:
      1. Check all Twilio credentials are present in config.
      2. Initialise a Twilio Client with the account credentials.
      3. Send the message from the WhatsApp sandbox number to
         MY_WHATSAPP_NUMBER.
      4. Log the Twilio message SID to confirm delivery.
      5. Return True on success, False on any failure.

    Args:
        message (str): English translation to deliver.
                       Example: "Did you eat today?"

    Returns:
        bool: True  → Twilio accepted the message (message SID logged).
              False → Credentials missing, Twilio error, or network issue.

    Example:
        success = send_text_message("Did you eat today?")
        if not success:
            logger.warning("WhatsApp delivery failed — will retry next cycle.")
    """
    if not _credentials_present():
        return False

    client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

    logger.info("Sending WhatsApp message...")

    try:
        # --- EXTERNAL CALL: Twilio WhatsApp API ---
        msg = client.messages.create(
            from_=config.TWILIO_WHATSAPP_FROM,
            to=config.MY_WHATSAPP_NUMBER,
            body=message,
        )
        # --- END EXTERNAL CALL ---

    except TwilioRestException as e:
        logger.error(
            "Twilio failed to send text message: %s\n"
            "Fix: Check the Twilio sandbox is active and the recipient has "
            "joined it — visit console.twilio.com to verify.",
            e,
        )
        return False

    logger.info("Delivered. WhatsApp message SID: %s", msg.sid)
    return True


def send_voice_note(audio_path: str) -> bool:
    """
    Sends a Mandarin AIFF file as a WhatsApp voice note.

    Twilio sends the audio as a media message (MMS). The file must be
    accessible via a public URL — Twilio fetches media from a URL, not
    from a local file path. For development, use ngrok or Twilio's media
    upload endpoint. The audio_path is passed as the media_url parameter.

    Steps:
      1. Check all Twilio credentials are present in config.
      2. Initialise a Twilio Client with the account credentials.
      3. Send the AIFF path as the media_url of a WhatsApp message.
      4. Log delivery confirmation and message SID.
      5. Return True on success, False on any failure.

    Args:
        audio_path (str): Path or URL to the AIFF voice note.
                          Example: "temp/reply.aiff"

    Returns:
        bool: True  → Twilio accepted the media message.
              False → Credentials missing, Twilio error, or network issue.

    Example:
        success = send_voice_note("temp/reply.aiff")
    """
    if not _credentials_present():
        return False

    client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

    logger.info("Sending voice note: %s", audio_path)

    try:
        # --- EXTERNAL CALL: Twilio WhatsApp API (media message) ---
        msg = client.messages.create(
            from_=config.TWILIO_WHATSAPP_FROM,
            to=config.MY_WHATSAPP_NUMBER,
            media_url=[audio_path],
        )
        # --- END EXTERNAL CALL ---

    except TwilioRestException as e:
        logger.error(
            "Twilio failed to send voice note '%s': %s\n"
            "Fix: The media_url must be publicly accessible. For local dev, "
            "expose the file with ngrok and update the URL.",
            audio_path,
            e,
        )
        return False

    logger.info("Voice note delivered. WhatsApp message SID: %s", msg.sid)
    return True


def send_mandarin_text(mandarin_text: str) -> bool:
    """
    Sends a Mandarin Chinese text message to the owner's WhatsApp number.

    Phase 1 fallback — sends Mandarin as text so the owner can show
    the screen to MIL. Voice notes require a public URL (ngrok or
    Brahma static IP) — Phase 2.

    Steps:
      1. Check all Twilio credentials are present in config.
      2. Initialise a Twilio Client with the account credentials.
      3. Send the Mandarin text from the WhatsApp sandbox number to
         MY_WHATSAPP_NUMBER.
      4. Log the Twilio message SID to confirm delivery.
      5. Return True on success, False on any failure.

    Args:
        mandarin_text (str): Mandarin translation to deliver as text.
                             Example: "我已经吃过了，谢谢。"

    Returns:
        bool: True  → Twilio accepted the message (message SID logged).
              False → Credentials missing, Twilio error, or network issue.

    Example:
        success = send_mandarin_text("你好")
        if not success:
            logger.warning("Mandarin text delivery failed.")
    """
    if not _credentials_present():
        return False

    client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

    logger.info("Sending Mandarin text to display to MIL...")

    try:
        # --- EXTERNAL CALL: Twilio WhatsApp API ---
        msg = client.messages.create(
            from_=config.TWILIO_WHATSAPP_FROM,
            to=config.MY_WHATSAPP_NUMBER,
            body=mandarin_text,
        )
        # --- END EXTERNAL CALL ---

    except TwilioRestException as e:
        logger.error(
            "Twilio failed to send Mandarin text message: %s\n"
            "Fix: Check the Twilio sandbox is active and the recipient has "
            "joined it — visit console.twilio.com to verify.",
            e,
        )
        return False

    logger.info("Mandarin text delivered. WhatsApp message SID: %s", msg.sid)
    return True


def _credentials_present() -> bool:
    """
    Returns True if all four Twilio credentials are loaded from .env.

    Called at the start of every send function so failures are caught
    before any API call is attempted — a missing credential would cause
    a confusing AuthenticationError deep inside the Twilio SDK otherwise.

    Steps:
      1. Check each credential is not None (os.getenv returns None if
         the variable is missing from .env).
      2. Log a specific error for any missing value.
      3. Return False if any credential is absent, True if all present.

    Args:
        None

    Returns:
        bool: True  → all credentials loaded and non-None.
              False → one or more credentials missing from .env.

    Example:
        if not _credentials_present():
            return False
    """
    # Credential values are never logged — only whether they are present.
    # Logging a Twilio auth token or account SID would expose it in
    # terminal history, log files, and any crash reports. The owner's
    # WhatsApp number is personal data and equally must stay out of logs.
    credentials = {
        "TWILIO_ACCOUNT_SID":   config.TWILIO_ACCOUNT_SID,
        "TWILIO_AUTH_TOKEN":    config.TWILIO_AUTH_TOKEN,
        "TWILIO_WHATSAPP_FROM": config.TWILIO_WHATSAPP_FROM,
        "MY_WHATSAPP_NUMBER":   config.MY_WHATSAPP_NUMBER,
    }

    missing = [name for name, value in credentials.items() if not value]

    if missing:
        logger.error(
            "Missing Twilio credentials: %s\n"
            "Fix: Add the missing values to your .env file. "
            "See .env.example for the required variable names.",
            ", ".join(missing),
        )
        return False

    return True
