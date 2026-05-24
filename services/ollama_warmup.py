# ============================================================
# FILE: services/ollama_warmup.py
#
# PURPOSE:
#   Keeps the Qwen3:14b model warm in Ollama so the first
#   real translation is fast (2-3s) instead of cold-start
#   slow (30-60s). Runs a background thread that sends a
#   lightweight ping to Ollama on startup, then re-pings
#   every N minutes to prevent the model from unloading.
#
# INPUTS:
#   None — reads OLLAMA_URL, OLLAMA_MODEL, and
#   OLLAMA_WARMUP_INTERVAL_MINUTES from config.py
#
# OUTPUTS:
#   Logs warmup status to the shared logger.
#   Returns True/False from warm_up_now() for callers
#   that need to know if Ollama is reachable.
#
# DEPENDENCIES:
#   - requests (pip install requests)
#   - config.py → OLLAMA_URL, OLLAMA_MODEL,
#                 OLLAMA_WARMUP_INTERVAL_MINUTES
#   - utils/logger.py
#
# CALLED BY:
#   - services/bot.py → on application startup
#
# AUTHOR: LingoBridge
# LAST UPDATED: 2026-05-24
# ============================================================

import threading
import time

import requests

import config
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Module-level state ────────────────────────────────────────────────────────
# Background thread handle — kept so we can check if it's alive.
_warmup_thread: threading.Thread | None = None

# Flag used to stop the background loop cleanly on shutdown.
_stop_event = threading.Event()


def warm_up_now() -> bool:
    """
    Sends a single lightweight request to Ollama to load Qwen3:14b
    into memory. Called once at startup and then on a timer.

    Steps:
      1. POST a minimal prompt to the Ollama /api/generate endpoint
      2. Use stream=False so we get one response (not token-by-token)
      3. Log success or failure with a human-readable message

    Args:
        None

    Returns:
        bool: True if Ollama responded successfully.
              False if Ollama is unreachable or returned an error.

    Raises:
        Nothing — all exceptions are caught and logged.

    Example:
        success = warm_up_now()
        if not success:
            logger.warning("Ollama not ready — translations will be slow")
    """

    # The warmup prompt is intentionally trivial — we just want the model
    # loaded into GPU/CPU memory. The response content doesn't matter.
    warmup_payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": "Hi",
        "stream": False,
    }

    try:
        logger.info(
            f"Warming up Ollama model '{config.OLLAMA_MODEL}' — "
            f"first run may take 30-60s..."
        )

        response = requests.post(
            f"{config.OLLAMA_URL}/api/generate",
            json=warmup_payload,
            timeout=config.OLLAMA_WARMUP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        logger.info(
            f"Ollama warmup complete — "
            f"'{config.OLLAMA_MODEL}' is loaded and ready."
        )
        return True

    except requests.exceptions.ConnectionError:
        logger.error(
            "Ollama warmup failed: cannot connect to Ollama. "
            "Fix: run 'ollama serve' in a terminal, then restart LingoBridge."
        )
        return False

    except requests.exceptions.Timeout:
        logger.warning(
            f"Ollama warmup timed out after "
            f"{config.OLLAMA_WARMUP_TIMEOUT_SECONDS}s. "
            "The model may still be loading. Translations will work "
            "once Ollama is ready."
        )
        return False

    except requests.exceptions.HTTPError as http_error:
        logger.error(
            f"Ollama warmup failed with HTTP error: {http_error}. "
            f"Check that model '{config.OLLAMA_MODEL}' is installed. "
            f"Fix: run 'ollama pull {config.OLLAMA_MODEL}'"
        )
        return False

    except Exception as unexpected_error:
        logger.error(
            f"Ollama warmup failed with unexpected error: {unexpected_error}"
        )
        return False


def _warmup_loop() -> None:
    """
    Background thread body. Warms up Ollama once at startup,
    then re-pings every OLLAMA_WARMUP_INTERVAL_MINUTES to keep
    the model loaded in memory.

    Steps:
      1. Run the first warmup immediately
      2. Sleep for the configured interval
      3. If the stop event is set, exit cleanly
      4. Otherwise, run another warmup and repeat

    Args:
        None

    Returns:
        None

    Raises:
        Nothing — all exceptions are handled inside warm_up_now().

    Example:
        This function is not called directly.
        Use start_warmup_scheduler() instead.
    """

    # Step 1: Warm up immediately when the bot starts
    warm_up_now()

    # Step 2: Re-ping on a timer to prevent Ollama from unloading the model
    interval_seconds = config.OLLAMA_WARMUP_INTERVAL_MINUTES * 60

    while True:
        # Sleep in 1-second chunks so we can respond to stop_event quickly
        for _ in range(interval_seconds):
            if _stop_event.is_set():
                logger.info("Ollama warmup scheduler stopped.")
                return
            time.sleep(1)

        # Keep the model alive with another ping
        logger.info("Running scheduled Ollama keep-alive ping...")
        warm_up_now()


def start_warmup_scheduler() -> None:
    """
    Starts the background warmup thread. Safe to call multiple times
    — if the thread is already running, this is a no-op.

    Steps:
      1. Check if a warmup thread is already running
      2. If not, clear the stop event and start a new daemon thread
      3. Log that the scheduler has started

    Args:
        None

    Returns:
        None

    Raises:
        Nothing.

    Example:
        # In bot.py startup:
        start_warmup_scheduler()
    """
    global _warmup_thread

    # Guard: don't start a second thread if one is already running
    if _warmup_thread is not None and _warmup_thread.is_alive():
        logger.info("Ollama warmup scheduler is already running.")
        return

    # Reset the stop flag in case we're restarting after a stop
    _stop_event.clear()

    # daemon=True means this thread won't prevent Python from exiting
    _warmup_thread = threading.Thread(
        target=_warmup_loop,
        name="OllamaWarmupThread",
        daemon=True,
    )
    _warmup_thread.start()

    logger.info(
        f"Ollama warmup scheduler started — "
        f"re-pinging every {config.OLLAMA_WARMUP_INTERVAL_MINUTES} minutes."
    )


def stop_warmup_scheduler() -> None:
    """
    Signals the background warmup thread to stop cleanly.
    Called during bot shutdown.

    Steps:
      1. Set the stop event — the loop will see this and exit
      2. Log that shutdown was requested

    Args:
        None

    Returns:
        None

    Raises:
        Nothing.

    Example:
        # In bot.py shutdown handler:
        stop_warmup_scheduler()
    """
    _stop_event.set()
    logger.info("Ollama warmup scheduler stop requested.")
