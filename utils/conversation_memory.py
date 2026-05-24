# ============================================================
# FILE: utils/conversation_memory.py
#
# PURPOSE:
#   Stores the last N exchanges between the owner and MIL so
#   Qwen3 can use recent context when translating. This allows
#   pronouns like "她" (she) or "那里" (there) to be resolved
#   correctly across consecutive messages.
#
#   Memory is held in a plain Python list — no database, no files.
#   It resets automatically when the session ends (/end command).
#
# INPUTS:
#   - mandarin (str): MIL's original Mandarin utterance
#   - english  (str): The English translation that was shown to owner
#
# OUTPUTS:
#   - get_context_block() → formatted multi-line string ready to
#     prepend to a translation prompt, or "" if memory is empty
#
# DEPENDENCIES:
#   - config.py → CONVERSATION_MEMORY_MAX_TURNS
#   - utils/logger.py
#
# CALLED BY:
#   - services/bot.py → after each successful round trip
#   - services/translate.py → to prepend context to prompts
#
# AUTHOR: LingoBridge
# LAST UPDATED: 2026-05-24
# ============================================================

from utils.logger import get_logger
import config

logger = get_logger(__name__)

# ── Module-level memory store ─────────────────────────────────────────────────
# Each entry is a dict with keys "mandarin" and "english".
# Oldest entries are dropped when the list exceeds MAX_TURNS.
# Example: [{"mandarin": "你好", "english": "Hello"}, ...]
_turns: list[dict[str, str]] = []


def add_turn(mandarin: str, english: str) -> None:
    """
    Adds one completed exchange to memory and trims old entries.

    A "turn" is one full round trip: MIL says something in Mandarin,
    the bot translates it to English. Both sides are stored together
    so the context block shows complete exchanges.

    Steps:
      1. Append the new turn as a dict to the memory list
      2. If the list is longer than MAX_TURNS, remove the oldest entry
      3. Log the current memory size

    Args:
        mandarin (str): MIL's Mandarin utterance.
                        Example: "你今晚要去哪里?"
        english  (str): The English translation shown to the owner.
                        Example: "Where are you going tonight?"

    Returns:
        None

    Raises:
        Nothing.

    Example:
        add_turn("你好吗？", "How are you?")
    """
    _turns.append({"mandarin": mandarin, "english": english})

    # Keep only the most recent MAX_TURNS exchanges.
    # Older context is less relevant and makes prompts unnecessarily long.
    while len(_turns) > config.CONVERSATION_MEMORY_MAX_TURNS:
        _turns.pop(0)

    logger.debug(
        "Memory updated — %d/%d turns stored.",
        len(_turns),
        config.CONVERSATION_MEMORY_MAX_TURNS,
    )


def get_context_block() -> str:
    """
    Returns a formatted string of recent exchanges to prepend to
    a translation prompt. Returns an empty string if memory is empty.

    The format is designed to be natural for an LLM to parse:

        Recent conversation context:
        [1] MIL (Mandarin): 你今晚要去哪里?
            Translation:    Where are you going tonight?
        [2] MIL (Mandarin): 几点回来?
            Translation:    What time are you coming back?

    Steps:
      1. If _turns is empty, return "" immediately
      2. Build a numbered list of exchanges
      3. Wrap in a context header and return

    Args:
        None

    Returns:
        str: Formatted context block, or "" if no turns are stored.

    Raises:
        Nothing.

    Example:
        context = get_context_block()
        if context:
            prompt = context + "\n\n" + base_prompt
    """
    if not _turns:
        return ""

    lines = ["Recent conversation context:"]

    for index, turn in enumerate(_turns, start=1):
        lines.append(
            f"[{index}] MIL (Mandarin): {turn['mandarin']}\n"
            f"    Translation:    {turn['english']}"
        )

    return "\n".join(lines)


def clear_memory() -> None:
    """
    Clears all stored turns. Called when the session ends (/end)
    so the next session starts with a clean slate.

    Steps:
      1. Clear the _turns list in place
      2. Log that memory was cleared

    Args:
        None

    Returns:
        None

    Raises:
        Nothing.

    Example:
        # In the /end command handler:
        clear_memory()
    """
    _turns.clear()
    logger.info("Conversation memory cleared.")


def get_turn_count() -> int:
    """
    Returns the number of turns currently in memory.
    Used by tests and debug logging.

    Args:
        None

    Returns:
        int: Number of stored turns. Example: 2

    Raises:
        Nothing.

    Example:
        logger.debug(f"Memory has {get_turn_count()} turns.")
    """
    return len(_turns)
