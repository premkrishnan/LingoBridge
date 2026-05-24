# ============================================================
# FILE: services/translate.py
#
# PURPOSE:
#   Sends text to the local Ollama / Qwen3 model and returns the
#   translation. Two public functions handle each direction:
#     - translate_to_english()  — Mandarin → English (forward mode)
#     - translate_to_mandarin() — English → Mandarin (reply mode)
#   Prompts live in config.py so tone can be tuned without touching
#   this file.
#
# INPUTS:
#   - mandarin_text (str): Mandarin Chinese text to translate to English
#   - english_text  (str): English text to translate to Mandarin
#
# OUTPUTS:
#   - translated_text (str): result from Ollama
#   - None: if Ollama is unreachable, times out, or returns an error
#
# DEPENDENCIES:
#   - requests (pip install requests)
#   - config.py → OLLAMA_API_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECS,
#                 TRANSLATE_TO_ENGLISH_PROMPT, TRANSLATE_TO_MANDARIN_PROMPT
#   - utils/logger.py
#   - utils/conversation_memory (optional context passed in by caller)
#
# CALLED BY:
#   - main.py → forward_pipeline(), reply_pipeline()
#
# AUTHOR: Clip Project
# LAST UPDATED: 2026-05-24
# ============================================================

import requests

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def translate_to_english(mandarin_text: str, context: str = "") -> str | None:
    """
    Translates Mandarin Chinese text to English via local Ollama.

    Steps:
      1. Format TRANSLATE_TO_ENGLISH_PROMPT with the input text.
      2. Prepend optional conversation context to the prompt.
      3. POST the prompt to Ollama with stream=False so the full
         response arrives in one JSON object (not a token stream).
      4. Extract the response text from the JSON payload.
      5. Strip whitespace and return the English translation.

    Args:
        mandarin_text (str): Mandarin text captured from MIL's speech.
                             Example: "你今天吃饭了吗？"
        context (str): Optional recent exchange history from
                       conversation_memory.get_context_block().
                       Pass "" (default) for no context.
                       Example: "Recent conversation context:\n[1] ..."

    Returns:
        str:  English translation. Example: "Did you eat today?"
        None: If Ollama is unreachable, times out, or returns an error.

    Example:
        english = translate_to_english("你好")
        if english:
            send_whatsapp_text(english)
    """
    base_prompt = config.TRANSLATE_TO_ENGLISH_PROMPT.format(text=mandarin_text)

    # Prepend recent conversation context if available.
    # This lets Qwen3 resolve pronouns like 她 (she) or 那里 (there)
    # by referring to earlier exchanges in the same session.
    if context:
        prompt = context + "\n\n" + base_prompt
    else:
        prompt = base_prompt

    return _call_ollama(prompt, label="Mandarin→English")


def translate_to_mandarin(english_text: str, context: str = "") -> str | None:
    """
    Translates English text to Mandarin Chinese via local Ollama.

    Steps:
      1. Format TRANSLATE_TO_MANDARIN_PROMPT with the input text.
      2. Prepend optional conversation context to the prompt.
      3. POST the prompt to Ollama with stream=False.
      4. Extract the response text from the JSON payload.
      5. Strip whitespace and return the Mandarin translation.

    Args:
        english_text (str): English reply spoken by the owner.
                            Example: "I already ate, thank you."
        context (str): Optional recent exchange history from
                       conversation_memory.get_context_block().
                       Pass "" (default) for no context.
                       Example: "Recent conversation context:\n[1] ..."

    Returns:
        str:  Mandarin translation. Example: "我已经吃过了，谢谢。"
        None: If Ollama is unreachable, times out, or returns an error.

    Example:
        mandarin = translate_to_mandarin("See you tomorrow")
        if mandarin:
            generate_mandarin_audio(mandarin)
    """
    base_prompt = config.TRANSLATE_TO_MANDARIN_PROMPT.format(text=english_text)

    # Prepend recent conversation context if available.
    if context:
        prompt = context + "\n\n" + base_prompt
    else:
        prompt = base_prompt

    return _call_ollama(prompt, label="English→Mandarin")


def _call_ollama(prompt: str, label: str) -> str | None:
    """
    POSTs a prompt to the Ollama API and returns the response text.

    Shared by both translation functions to avoid duplicating the
    HTTP call, error handling, and logging (SKILL.md 1.2).

    Steps:
      1. Build the request payload with model name and stream=False.
      2. POST to OLLAMA_API_URL with the configured timeout.
      3. Raise on non-2xx HTTP status.
      4. Extract and return the "response" field from the JSON body.

    Args:
        prompt (str): Fully formatted prompt string ready to send.
        label (str):  Human-readable direction label for log lines.
                      Example: "Mandarin→English"

    Returns:
        str:  The translation text returned by Ollama.
        None: On any connection, timeout, or HTTP error.

    Example:
        result = _call_ollama(formatted_prompt, "Mandarin→English")
    """
    # "think": False disables Qwen3's built-in reasoning mode, which
    # deliberates before answering and adds 5-8s of silent latency with
    # no quality benefit for translation. The Ollama API accepts this as
    # a top-level field — no /no_think prompt prefix needed.
    payload = {
        "model":  config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "think":  False,
    }

    logger.info("Calling Ollama (%s) [%s]...", config.OLLAMA_MODEL, label)

    try:
        # --- EXTERNAL CALL: Ollama / Qwen3 translation ---
        response = requests.post(
            config.OLLAMA_API_URL,
            json=payload,
            timeout=config.OLLAMA_TIMEOUT_SECS,
        )
        response.raise_for_status()
        # --- END EXTERNAL CALL ---

    except requests.exceptions.ConnectionError:
        logger.error(
            "Cannot reach Ollama at %s\n"
            "Fix: Run 'ollama serve' in a terminal, then retry.",
            config.OLLAMA_API_URL,
        )
        return None

    except requests.exceptions.Timeout:
        logger.error(
            "Ollama did not respond within %ds.\n"
            "Fix: The model may still be loading — wait 30s and try again.",
            config.OLLAMA_TIMEOUT_SECS,
        )
        return None

    except requests.exceptions.HTTPError as e:
        logger.error(
            "Ollama returned an HTTP error: %s\n"
            "Fix: Check that model '%s' is pulled — run: ollama pull %s",
            e,
            config.OLLAMA_MODEL,
            config.OLLAMA_MODEL,
        )
        return None

    translation = response.json().get("response", "").strip()

    if not translation:
        logger.warning(
            "Ollama returned an empty response for [%s] — skipping.", label
        )
        return None

    logger.info("Translation [%s]: %s", label, translation)
    return translation
