# ============================================================
# FILE: tests/test_transcribe.py
#
# PURPOSE:
#   Unit tests for services/transcribe.py.
#   Verifies Whisper STT integration, language filtering (zh only),
#   and error handling — without running the real Whisper model.
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
#   - services/transcribe.py
#
# CALLED BY:
#   - pytest (run: pytest tests/test_transcribe.py)
#
# AUTHOR: Clip Project
# LAST UPDATED: 2026-05-23
# ============================================================
