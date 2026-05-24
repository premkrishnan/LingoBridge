# ============================================================
# FILE: tests/test_tts.py
#
# PURPOSE:
#   Unit tests for services/tts.py.
#   Verifies Kokoro TTS calls, macOS 'say' fallback, and error
#   handling — without generating real audio.
#
# INPUTS:
#   None (pytest discovers and runs these automatically)
#
# OUTPUTS:
#   - Pass/fail test results via pytest
#
# DEPENDENCIES:
#   - pytest (pip install pytest)
#   - unittest.mock (Python standard library)
#   - services/tts.py
#
# CALLED BY:
#   - pytest (run: pytest tests/test_tts.py)
#
# AUTHOR: Clip Project
# LAST UPDATED: 2026-05-23
# ============================================================
