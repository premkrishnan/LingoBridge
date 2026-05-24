# ============================================================
# FILE: tests/test_conversation_memory.py
#
# PURPOSE:
#   Unit tests for utils/conversation_memory.py.
#   Verifies that turns are stored, trimmed, formatted, and
#   cleared correctly — no external services needed.
#
# DEPENDENCIES:
#   - pytest
#   - utils/conversation_memory.py
#   - config.py → CONVERSATION_MEMORY_MAX_TURNS
#
# CALLED BY:
#   pytest (run: python -m pytest tests/test_conversation_memory.py -v)
#
# AUTHOR: LingoBridge
# LAST UPDATED: 2026-05-24
# ============================================================

import pytest

import config
from utils.conversation_memory import (
    add_turn,
    clear_memory,
    get_context_block,
    get_turn_count,
)


@pytest.fixture(autouse=True)
def reset_memory_between_tests():
    """
    Clears conversation memory before every test so tests
    don't interfere with each other.
    """
    clear_memory()
    yield
    clear_memory()


class TestAddTurn:
    """Tests for add_turn()."""

    def test_adding_one_turn_stores_it(self):
        """
        After adding one turn, get_turn_count() should return 1.
        """
        add_turn("你好吗？", "How are you?")
        assert get_turn_count() == 1

    def test_adding_multiple_turns_stores_all_within_limit(self):
        """
        Adding up to MAX_TURNS turns should store all of them.
        """
        for i in range(config.CONVERSATION_MEMORY_MAX_TURNS):
            add_turn(f"Mandarin {i}", f"English {i}")

        assert get_turn_count() == config.CONVERSATION_MEMORY_MAX_TURNS

    def test_exceeding_max_turns_drops_oldest(self):
        """
        When we add more turns than MAX_TURNS, the oldest turn
        should be dropped so the count stays at MAX_TURNS.
        """
        # Fill memory to the limit
        for i in range(config.CONVERSATION_MEMORY_MAX_TURNS):
            add_turn(f"Mandarin {i}", f"English {i}")

        # Add one more — oldest should be dropped
        add_turn("New Mandarin", "New English")

        assert get_turn_count() == config.CONVERSATION_MEMORY_MAX_TURNS

    def test_oldest_turn_is_dropped_not_newest(self):
        """
        When memory overflows, it's the oldest turn that disappears
        — not the most recent one.
        """
        add_turn("First Mandarin", "First English")

        for i in range(config.CONVERSATION_MEMORY_MAX_TURNS):
            add_turn(f"Later {i}", f"Later English {i}")

        # The context block should not contain the first turn
        context = get_context_block()
        assert "First Mandarin" not in context
        assert "First English" not in context


class TestGetContextBlock:
    """Tests for get_context_block()."""

    def test_returns_empty_string_when_memory_is_empty(self):
        """
        With no turns stored, get_context_block() should return ""
        so callers can safely check `if context:` before prepending.
        """
        result = get_context_block()
        assert result == ""

    def test_context_block_contains_mandarin_text(self):
        """
        After adding a turn, the context block should contain
        the Mandarin text so Qwen3 can see it.
        """
        add_turn("你今晚要去哪里?", "Where are you going tonight?")
        context = get_context_block()
        assert "你今晚要去哪里?" in context

    def test_context_block_contains_english_translation(self):
        """
        After adding a turn, the context block should contain
        the English translation alongside the Mandarin.
        """
        add_turn("你今晚要去哪里?", "Where are you going tonight?")
        context = get_context_block()
        assert "Where are you going tonight?" in context

    def test_context_block_contains_header(self):
        """
        The context block should start with the header line so
        Qwen3 understands what the block represents.
        """
        add_turn("你好", "Hello")
        context = get_context_block()
        assert "Recent conversation context:" in context

    def test_context_block_numbers_turns(self):
        """
        Multiple turns should be numbered [1], [2], [3] so
        Qwen3 can follow the conversation order.
        """
        add_turn("你好", "Hello")
        add_turn("几点了？", "What time is it?")
        context = get_context_block()
        assert "[1]" in context
        assert "[2]" in context

    def test_context_block_orders_oldest_first(self):
        """
        Turns should appear in chronological order (oldest first)
        so Qwen3 reads the conversation naturally.
        """
        add_turn("First message", "First English")
        add_turn("Second message", "Second English")
        context = get_context_block()

        first_position = context.index("First message")
        second_position = context.index("Second message")
        assert first_position < second_position


class TestClearMemory:
    """Tests for clear_memory()."""

    def test_clear_removes_all_turns(self):
        """
        After calling clear_memory(), get_turn_count() should
        return 0 regardless of how many turns were stored.
        """
        add_turn("你好", "Hello")
        add_turn("再见", "Goodbye")

        clear_memory()

        assert get_turn_count() == 0

    def test_clear_makes_context_block_empty(self):
        """
        After clear_memory(), get_context_block() should return ""
        so no stale context bleeds into the next session.
        """
        add_turn("你好", "Hello")
        clear_memory()

        assert get_context_block() == ""

    def test_clear_on_empty_memory_does_not_crash(self):
        """
        Calling clear_memory() when nothing is stored should
        be a no-op — not raise an exception.
        """
        clear_memory()  # Already empty from fixture
        clear_memory()  # Second call — should not crash
        assert get_turn_count() == 0
