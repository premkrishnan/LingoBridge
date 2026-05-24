# ============================================================
# FILE: config.py
#
# PURPOSE:
#   Single source of truth for all project settings, constants,
#   and secrets. Reads credentials from .env via python-dotenv.
#   All other modules import constants from here — never from .env.
#
# INPUTS:
#   - .env file (Twilio credentials loaded via load_dotenv)
#
# OUTPUTS:
#   - Module-level constants used across the entire project
#
# DEPENDENCIES:
#   - python-dotenv (pip install python-dotenv)
#   - pathlib (Python standard library)
#
# CALLED BY:
#   - All service and utility modules
#
# AUTHOR: Clip Project
# LAST UPDATED: 2026-05-24
# ============================================================

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file so os.getenv() calls below return real values.
# Must happen before any os.getenv() call in this file.
load_dotenv()


# ── Project identity ──────────────────────────────────────────
PROJECT_NAME = "LingoBridge"
VERSION      = "0.1.0"


# ── Audio ─────────────────────────────────────────────────────

# Whisper requires exactly 16kHz mono audio.
# Any other sample rate causes silent transcription failures.
SAMPLE_RATE = 16000

# Whisper requires a single (mono) audio channel.
# Stereo input must be downmixed before passing to Whisper.
CHANNELS = 1

# Seconds of silence before the recording is considered finished.
# 1.5s feels natural — enough pause after a spoken sentence.
# Too short (< 1s) cuts off speech; too long (> 3s) feels laggy.
SILENCE_THRESHOLD_SECS = 1.5

# Recordings shorter than this (seconds) are ignored entirely.
# Prevents sending noise bursts and breath sounds to Whisper.
MIN_RECORDING_SECS = 0.5

# iPhone via Continuity Camera — better mic for capturing MIL's
# voice across a table. Index 1 = MacBook built-in mic (fallback
# if iPhone not connected).
# Run: python utils/list_audio_devices.py to confirm indices.
MIC_DEVICE_INDEX = 0

# Paths use pathlib.Path — never raw string concatenation.
# Relative to the project root where main.py is run from.
TEMP_INPUT_AUDIO = Path("temp") / "input.wav"

# macOS say command outputs AIFF natively. WhatsApp accepts AIFF
# voice notes on iPhone. Change to reply.mp3 on Brahma where
# Qwen3-TTS outputs MP3.
TEMP_REPLY_AUDIO = Path("temp") / "reply.aiff"

# M4A/AAC format for Telegram send_audio().
# Converted from reply.aiff using afconvert -f m4af -d aac.
# OGG/OPUS and MP3 encoding not supported by afconvert on macOS Tahoe.
TEMP_REPLY_M4A = Path("temp") / "reply.m4a"


# ── Whisper (Speech-to-Text) ──────────────────────────────────

# large-v3 gives the best Mandarin accuracy of all Whisper sizes.
# Runs in ~2-4s per sentence on M4 CPU — fast enough for real-time.
WHISPER_MODEL = "large-v3"

# Mac M4: faster-whisper does not support Apple Metal (MPS).
# Use "cpu" here. Switch to "cuda" when migrating to Brahma (ROCm
# auto-maps "cuda" to HIP on AMD GPUs).
WHISPER_DEVICE = "cpu"

# int8 is required for CPU inference on Mac M4.
# faster-whisper emits a performance warning when float16 is used on CPU
# because float16 is not natively accelerated on CPU hardware.
# On Brahma (GPU), switch back to "float16" for best speed and accuracy.
WHISPER_COMPUTE_TYPE = "int8"

# BCP-47 language code for Mandarin Chinese.
# Used to reject audio that is not Mandarin (avoids mis-translations).
MANDARIN_LANGUAGE_CODE = "zh"


# ── Ollama / Qwen3 (Translation LLM) ─────────────────────────

# Ollama's local HTTP API endpoint — same URL on Mac and Brahma.
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# qwen3:14b — better translation quality for idiomatic Mandarin
# family conversation. 8b is faster but 14b fits comfortably in
# 24GB unified RAM on M4.
OLLAMA_MODEL = "qwen3:14b"
OLLAMA_URL   = "http://localhost:11434"   # ← add this line for health checks and warmup pings.

# qwen3:14b needs up to 90s on first load into RAM. Subsequent
# calls are 1-3s once model is warm. Increase to 120 to safely
# cover cold start.
OLLAMA_TIMEOUT_SECS = 120

# How long (seconds) to wait for Ollama warmup ping on startup.
# First cold-start can take 30-60s. Set this higher to be safe.
OLLAMA_WARMUP_TIMEOUT_SECONDS = 90

# How often (minutes) the scheduler re-pings Ollama to keep
# the model loaded. Ollama unloads after ~5 min of inactivity.
OLLAMA_WARMUP_INTERVAL_MINUTES = 4


# ── TTS (Mandarin Text-to-Speech) ─────────────────────────────

# Controls which TTS engine is used.
# "say"   → macOS built-in Ting-Ting Mandarin voice — no installation
#            required. Works on Python 3.13 where kokoro fails
#            (blis/spacy incompatibility). Change to "qwen3" on Brahma.
# "qwen3" → Qwen3-TTS HTTP API on Brahma (requires ROCm Docker).
TTS_BACKEND = "say"

# Qwen3-TTS API endpoint — only used when TTS_BACKEND = "qwen3".
# Ignored on Mac (Kokoro is called as a Python library, not HTTP).
TTS_URL = "http://localhost:8880/v1/audio/speech"

# macOS built-in Mandarin voice — confirmed working on macOS Tahoe.
# Other options: 'Grandma (Chinese (China mainland))' for a warmer
# elderly voice. Voice name has no hyphen — 'Ting-Ting' fails,
# 'Tingting' works.
# On Brahma (TTS_BACKEND = "qwen3"), replace with a Qwen3-TTS voice preset.
TTS_VOICE = "Tingting"

# Maximum seconds to wait for TTS to return audio (normal runs).
TTS_TIMEOUT_SECS = 20

# Extended timeout for the very first TTS request after startup.
# Qwen3-TTS runs torch.compile on first use — takes ~75s on Brahma.
# Not relevant on Mac (Kokoro has no compile step).
TTS_STARTUP_TIMEOUT = 120

# CRITICAL — prevents a known ROCm performance bug in Qwen3-TTS.
# Values 64, 66, 67, 71, or 80 cause 5-10x slowdown on AMD GPUs.
# 72 is the safe value confirmed to avoid the bug.
# Only applies on Brahma; harmless to keep defined on Mac.
TTS_DECODE_WINDOW_FRAMES = 72


# ── WhatsApp / Twilio ─────────────────────────────────────────
# All credentials are loaded from .env — never hardcoded here.
# If any value is None, Twilio calls will fail with a clear error.

TWILIO_ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM")
MY_WHATSAPP_NUMBER   = os.getenv("MY_WHATSAPP_NUMBER")


# ── Telegram Bot ──────────────────────────────────────────────
# Token from @BotFather. Loaded from .env — never hardcoded.
# Create a bot: https://t.me/BotFather → /newbot → copy the token.
# If None, bot.py will fail with a clear error at startup.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Chat action shown while bot is transcribing/translating.
# Displays "typing…" indicator so owner knows the bot is working.
TELEGRAM_ACTION_TRANSLATING = "typing"

# Chat action shown while bot is sending the TTS voice note.
# Displays "sending voice…" indicator during audio upload.
TELEGRAM_ACTION_SPEAKING = "upload_voice"


# ── Translation prompts ───────────────────────────────────────
# Stored here so prompt wording can be tuned without touching
# service code. Thinking mode is disabled via "think": False in
# the Ollama payload (translate.py) — no /no_think prefix needed.
# Prompts are intentionally strict to prevent Qwen3 from adding
# extra sentences beyond the source text.

TRANSLATE_TO_ENGLISH_PROMPT = (
    "You are a translator. Translate ONLY the exact text provided. "
    "Do not add explanations, extra sentences, greetings, or anything "
    "not in the original. Output only the translation, nothing else.\n\n"
    "Translate this Mandarin Chinese text to English:\n{text}"
)

TRANSLATE_TO_MANDARIN_PROMPT = (
    "You are a translator. Translate ONLY the exact text provided. "
    "Do not add explanations, extra sentences, or anything not in "
    "the original. Output only the translation, nothing else.\n\n"
    "Translate this English text to Mandarin Chinese:\n{text}"
)
