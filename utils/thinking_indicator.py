# ============================================================
# FILE: utils/thinking_indicator.py
#
# PURPOSE:
#   Sends a continuous Telegram "typing" or "recording voice"
#   indicator to the user while the bot is busy doing slow
#   work (Whisper transcription, Ollama translation, TTS).
#
#   Telegram indicators auto-cancel after ~5 seconds, so this
#   module re-sends them every 4 seconds on a background thread
#   until the caller calls stop().
#
# INPUTS:
#   - context (CallbackContext): Telegram bot context object
#   - chat_id (int): Telegram chat ID to send the indicator to
#   - action (str): Telegram chat action string, e.g. "typing"
#                   or "upload_voice". Use constants from config.py.
#
# OUTPUTS:
#   - Sends repeated chat action signals to Telegram.
#   - No return value.
#
# DEPENDENCIES:
#   - python-telegram-bot
#   - config.py → TELEGRAM_ACTION_TRANSLATING, TELEGRAM_ACTION_SPEAKING
#   - utils/logger.py
#
# CALLED BY:
#   - services/bot.py → inside voice message handler
#
# AUTHOR: LingoBridge
# LAST UPDATED: 2026-05-24
# ============================================================

import asyncio
import threading

from utils.logger import get_logger

logger = get_logger(__name__)

# Telegram drops the indicator after ~5 seconds, so we re-send
# every 4 seconds to keep it visible throughout long operations.
_INDICATOR_REFRESH_SECONDS = 4


class ThinkingIndicator:
    """
    Context manager that shows a Telegram chat action indicator
    (e.g. "typing..." or "recording voice...") while a slow
    operation is running.

    Usage:
        async with ThinkingIndicator(context, chat_id, "typing"):
            result = await slow_function()

    The indicator starts when the block is entered and stops
    automatically when the block exits — even if an exception occurs.
    """

    def __init__(self, context, chat_id: int, action: str) -> None:
        """
        Initialise the indicator but do not start it yet.

        Args:
            context: Telegram bot context from the handler.
            chat_id (int): The chat to send the indicator to.
                           Example: 1038568926
            action (str):  Telegram chat action string.
                           Example: "typing" or "upload_voice"

        Returns:
            None

        Raises:
            Nothing — errors during send are caught and logged.

        Example:
            indicator = ThinkingIndicator(context, chat_id, "typing")
        """
        self._context = context
        self._chat_id = chat_id
        self._action = action
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None

    async def _send_loop(self) -> None:
        """
        Repeatedly sends the chat action every 4 seconds until
        the stop event is set.

        Steps:
          1. Send the chat action immediately
          2. Wait 4 seconds (or until stop is requested)
          3. If stop was requested, exit
          4. Otherwise, send again and repeat

        Args:
            None

        Returns:
            None

        Raises:
            Nothing — all exceptions are caught.

        Example:
            This is called internally by __aenter__.
        """
        while not self._stop_event.is_set():
            try:
                await self._context.bot.send_chat_action(
                    chat_id=self._chat_id,
                    action=self._action,
                )
            except Exception as send_error:
                # Don't crash the bot if the indicator fails to send.
                # Log at debug level — this is non-critical.
                logger.debug(
                    f"Thinking indicator send failed (non-critical): "
                    f"{send_error}"
                )

            # Wait 4 seconds, but wake immediately if stop is requested
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=_INDICATOR_REFRESH_SECONDS,
                )
            except asyncio.TimeoutError:
                # Timeout is expected — means we should send again
                pass

    async def __aenter__(self) -> "ThinkingIndicator":
        """
        Start the indicator loop as a background asyncio task.

        Steps:
          1. Clear the stop event
          2. Schedule _send_loop as a background task

        Args:
            None

        Returns:
            self: The indicator instance (not usually needed).

        Raises:
            Nothing.

        Example:
            async with ThinkingIndicator(ctx, chat_id, "typing") as ind:
                ...
        """
        self._stop_event.clear()
        self._task = asyncio.create_task(self._send_loop())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Stop the indicator loop when the 'async with' block exits.

        Steps:
          1. Set the stop event so _send_loop exits cleanly
          2. Cancel the background task
          3. Await the task to ensure clean teardown

        Args:
            exc_type: Exception type if one was raised (or None).
            exc_val:  Exception value if one was raised (or None).
            exc_tb:   Traceback if one was raised (or None).

        Returns:
            None (does not suppress exceptions)

        Raises:
            Nothing.

        Example:
            Called automatically when the 'async with' block ends.
        """
        self._stop_event.set()

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                # CancelledError is expected here — the task was cancelled
                pass

        logger.debug(f"Thinking indicator stopped for chat {self._chat_id}.")
