# ============================================================
# FILE: tests/test_ollama_warmup.py
#
# PURPOSE:
#   Unit tests for services/ollama_warmup.py.
#   Verifies warmup success/failure paths and scheduler
#   start/stop lifecycle — all without hitting real Ollama.
#
# INPUTS:
#   None — uses unittest.mock to fake HTTP responses.
#
# OUTPUTS:
#   Pass/fail test results via pytest.
#
# DEPENDENCIES:
#   - pytest
#   - unittest.mock
#   - services/ollama_warmup.py
#   - config.py
#
# CALLED BY:
#   pytest (run: pytest tests/test_ollama_warmup.py -v)
#
# AUTHOR: LingoBridge
# LAST UPDATED: 2026-05-24
# ============================================================

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

import config
from services.ollama_warmup import (
    start_warmup_scheduler,
    stop_warmup_scheduler,
    warm_up_now,
)


class TestWarmUpNow:
    """Tests for the warm_up_now() function."""

    def test_warm_up_returns_true_when_ollama_responds(self):
        """
        When Ollama responds with HTTP 200, warm_up_now() should
        return True to signal the model is ready.
        """
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None

        with patch("services.ollama_warmup.requests.post", return_value=mock_response):
            result = warm_up_now()

        assert result is True

    def test_warm_up_returns_false_when_ollama_is_not_running(self):
        """
        When Ollama is not running and connection is refused,
        warm_up_now() should return False — not raise an exception.
        This ensures the bot starts even if Ollama isn't ready yet.
        """
        import requests as req_module

        with patch(
            "services.ollama_warmup.requests.post",
            side_effect=req_module.exceptions.ConnectionError("refused"),
        ):
            result = warm_up_now()

        assert result is False

    def test_warm_up_returns_false_on_timeout(self):
        """
        When Ollama takes too long to respond, warm_up_now()
        should return False and log a warning — not block forever.
        """
        import requests as req_module

        with patch(
            "services.ollama_warmup.requests.post",
            side_effect=req_module.exceptions.Timeout("too slow"),
        ):
            result = warm_up_now()

        assert result is False

    def test_warm_up_returns_false_on_http_error(self):
        """
        When Ollama returns a non-200 HTTP error (e.g. model not
        found), warm_up_now() should return False and log the error.
        """
        import requests as req_module

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = req_module.exceptions.HTTPError(
            "404 model not found"
        )

        with patch("services.ollama_warmup.requests.post", return_value=mock_response):
            result = warm_up_now()

        assert result is False


class TestWarmupScheduler:
    """Tests for the start/stop scheduler lifecycle."""

    def test_scheduler_starts_a_background_thread(self):
        """
        After calling start_warmup_scheduler(), a daemon thread
        named 'OllamaWarmupThread' should be running.
        """
        # Mock warm_up_now so the thread doesn't actually call Ollama
        with patch("services.ollama_warmup.warm_up_now", return_value=True):
            start_warmup_scheduler()

            # Give the thread a moment to start
            time.sleep(0.1)

            running_thread_names = [t.name for t in threading.enumerate()]
            assert "OllamaWarmupThread" in running_thread_names

            # Clean up
            stop_warmup_scheduler()

    def test_starting_scheduler_twice_does_not_create_two_threads(self):
        """
        Calling start_warmup_scheduler() a second time while the
        thread is already running should be a no-op — not start
        a duplicate thread.
        """
        with patch("services.ollama_warmup.warm_up_now", return_value=True):
            start_warmup_scheduler()
            start_warmup_scheduler()

            time.sleep(0.1)

            warmup_threads = [
                t for t in threading.enumerate()
                if t.name == "OllamaWarmupThread"
            ]
            assert len(warmup_threads) == 1

            stop_warmup_scheduler()

    def test_stop_scheduler_signals_thread_to_exit(self):
        """
        After calling stop_warmup_scheduler(), the stop event
        should be set so the background thread can exit cleanly.
        """
        from services import ollama_warmup

        with patch("services.ollama_warmup.warm_up_now", return_value=True):
            start_warmup_scheduler()
            time.sleep(0.1)

            stop_warmup_scheduler()

            # The stop event should be set
            assert ollama_warmup._stop_event.is_set()


class TestThinkingIndicator:
    """Tests for utils/thinking_indicator.py."""

    @pytest.mark.asyncio
    async def test_indicator_sends_chat_action_on_enter(self):
        """
        When entering the 'async with ThinkingIndicator' block,
        at least one send_chat_action call should be made to Telegram.
        """
        from utils.thinking_indicator import ThinkingIndicator

        mock_bot = MagicMock()
        mock_bot.send_chat_action = MagicMock(return_value=_async_none())

        mock_context = MagicMock()
        mock_context.bot = mock_bot

        async with ThinkingIndicator(mock_context, chat_id=12345, action="typing"):
            # Give the loop one iteration to fire
            import asyncio
            await asyncio.sleep(0.05)

        assert mock_bot.send_chat_action.called

    @pytest.mark.asyncio
    async def test_indicator_stops_on_exit(self):
        """
        When the 'async with' block exits, the indicator should
        stop sending — even if an exception was raised inside the block.
        """
        from utils.thinking_indicator import ThinkingIndicator
        import asyncio

        mock_bot = MagicMock()
        mock_bot.send_chat_action = MagicMock(return_value=_async_none())

        mock_context = MagicMock()
        mock_context.bot = mock_bot

        indicator = ThinkingIndicator(mock_context, chat_id=12345, action="typing")

        try:
            async with indicator:
                await asyncio.sleep(0.05)
                raise ValueError("simulated error inside block")
        except ValueError:
            pass  # Expected — we're testing that the indicator still stops

        # After the block, the stop event should be set
        assert indicator._stop_event.is_set()


# ── Helper ────────────────────────────────────────────────────────────────────

async def _async_none():
    """Returns None — used to make MagicMock awaitable in tests."""
    return None
