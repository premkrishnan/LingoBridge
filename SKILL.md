---
name: lingobridge-coding-standards
description: >
  Coding standards, structure rules, documentation requirements,
  and hardware-specific guidelines for the LingoBridge project.
  Claude Code MUST read and follow every rule in this file before
  writing, editing, or refactoring any code in the LingoBridge codebase.
  Covers: file structure, commenting, error handling, logging, naming
  conventions, config management, testing, and Brahma AMD ROCm quirks.
version: "1.0"
project: LingoBridge
last_updated: "2026-05-23"
---

# SKILL.md — LingoBridge Coding Standards
# ============================================================
# This file defines the laws Claude Code must follow when
# writing, editing, or refactoring ANY code in this project.
#
# These rules exist to keep the codebase:
#   - Easy to read by a non-expert
#   - Easy to debug when something breaks
#   - Easy to extend with new features
#   - Consistent across all files
#
# Claude Code MUST follow every rule here, every time,
# without exception, unless explicitly overridden per-task.
# ============================================================


# ─────────────────────────────────────────────────────────────
# SECTION 1 — PHILOSOPHY
# ─────────────────────────────────────────────────────────────

## 1.1 Clarity over cleverness
# Always prefer the simple, obvious solution over a clever one.
# If a junior developer (or the owner, who is not a full-time
# programmer) cannot read a function and understand it in under
# 30 seconds, rewrite it to be simpler.

## 1.2 One thing per function
# Every function does exactly one thing.
# If you can describe a function with the word "and", it should
# be split into two functions.
#
# GOOD:  capture_audio()   →  records mic until silence
#        save_audio()      →  writes audio to disk
#
# BAD:   capture_and_save_audio()  →  does both (split it)

## 1.3 Fail loudly, fail clearly
# When something goes wrong, the error message must tell the
# owner EXACTLY what broke and WHY — not a cryptic traceback.
# Every service call (Whisper, Ollama, TTS, WhatsApp) must have
# a try/except that prints a human-readable explanation.

## 1.4 No magic values
# Never hardcode a number, URL, model name, or file path
# directly inside a function. All such values live in config.py
# or the .env file. This way, changing a setting means editing
# one place, not hunting through code.

## 1.5 Explicit is better than implicit
# Never write code that "figures things out" silently.
# If a decision is being made (e.g. language detected, silence
# threshold triggered), print a short log line saying so.


# ─────────────────────────────────────────────────────────────
# SECTION 2 — FILE AND FOLDER STRUCTURE
# ─────────────────────────────────────────────────────────────

## Required project layout:
#
# clip-project/
# │
# ├── SKILL.md              ← This file. Coding law.
# ├── CLAUDE.md             ← Project context for Claude Code
# ├── README.md             ← Human setup guide
# ├── .env                  ← API keys and secrets (never commit)
# ├── .env.example          ← Template showing required keys
# ├── config.py             ← All settings, paths, model names
# ├── main.py               ← Entry point. Runs the pipeline loop
# │
# ├── services/             ← One file per external service
# │   ├── __init__.py
# │   ├── audio_capture.py  ← Microphone recording
# │   ├── transcribe.py     ← Whisper STT (Mandarin → text)
# │   ├── translate.py      ← Ollama LLM (text → text)
# │   ├── tts.py            ← Qwen3-TTS (text → Mandarin audio)
# │   └── whatsapp.py       ← Twilio WhatsApp send/receive
# │
# ├── utils/                ← Shared helpers used across services
# │   ├── __init__.py
# │   ├── logger.py         ← Centralised logging setup
# │   └── audio_utils.py    ← WAV conversion, silence detection
# │
# ├── tests/                ← One test file per service
# │   ├── test_audio_capture.py
# │   ├── test_transcribe.py
# │   ├── test_translate.py
# │   ├── test_tts.py
# │   └── test_whatsapp.py
# │
# └── temp/                 ← Temporary audio files (auto-cleared)
#     └── .gitkeep

## Rules:
# - NEVER put logic inside main.py beyond calling service functions
# - NEVER put two services in the same file
# - NEVER import from services/ into services/ (no circular deps)
# - utils/ is the only shared code; services/ never import each other
# - temp/ files are deleted after each pipeline run
# - .env is NEVER committed to git (add to .gitignore immediately)


# ─────────────────────────────────────────────────────────────
# SECTION 3 — FILE HEADER STANDARD
# ─────────────────────────────────────────────────────────────

## Every .py file MUST begin with this exact header format:
#
# ============================================================
# FILE: services/transcribe.py
#
# PURPOSE:
#   Receives a WAV audio file path, sends it to the local
#   Whisper Large-v3 model, and returns the Mandarin transcript
#   as a plain string.
#
# INPUTS:
#   - audio_path (str): path to a 16kHz mono WAV file
#
# OUTPUTS:
#   - transcript (str): Mandarin text from the audio
#   - None: if language is not Mandarin or audio is silent
#
# DEPENDENCIES:
#   - faster-whisper (pip install faster-whisper)
#   - config.py → WHISPER_MODEL, WHISPER_DEVICE
#
# CALLED BY:
#   - main.py → forward_pipeline()
#
# AUTHOR: Clip Project
# LAST UPDATED: [date]
# ============================================================

## This header must be present and accurate in every file.
## Claude Code must update LAST UPDATED when editing a file.


# ─────────────────────────────────────────────────────────────
# SECTION 4 — FUNCTION DOCUMENTATION STANDARD
# ─────────────────────────────────────────────────────────────

## Every function MUST have a docstring in this format:
#
# def transcribe_audio(audio_path: str) -> str | None:
#     """
#     Sends a WAV file to local Whisper and returns Mandarin text.
#
#     Steps:
#       1. Load audio file from disk
#       2. Run Whisper inference (language detection + transcription)
#       3. If detected language is not 'zh', return None
#       4. Return the transcript string
#
#     Args:
#         audio_path (str): Full path to a 16kHz mono WAV file.
#                           Example: "/home/user/clip/temp/input.wav"
#
#     Returns:
#         str:  Mandarin transcript if language is Chinese.
#               Example: "你今天吃饭了吗？"
#         None: If audio is not Mandarin or is silent.
#
#     Raises:
#         FileNotFoundError: If audio_path does not exist.
#         RuntimeError:      If Whisper model fails to load.
#
#     Example:
#         transcript = transcribe_audio("/tmp/mil_speech.wav")
#         if transcript:
#             print(f"MIL said: {transcript}")
#     """

## Rules:
# - No function without a docstring, no exceptions
# - "Steps:" section is mandatory — it explains the logic before reading code
# - Args and Returns must show a real example value, not just type
# - If a function has no arguments, write "Args: None"


# ─────────────────────────────────────────────────────────────
# SECTION 5 — INLINE COMMENTING RULES
# ─────────────────────────────────────────────────────────────

## 5.1 Comment the WHY, not the WHAT
# The code shows WHAT is happening. Comments explain WHY.
#
# BAD:
#   sample_rate = 16000  # set sample rate to 16000
#
# GOOD:
#   # Whisper requires exactly 16kHz mono audio.
#   # Any other sample rate will cause silent transcription failures.
#   sample_rate = 16000

## 5.2 Comment before every logical block
# Every distinct step inside a function gets a short comment above it.
#
# GOOD:
#   # Step 1: Load the audio file into memory
#   audio_data = load_wav(audio_path)
#
#   # Step 2: Run Whisper — this takes 1-3 seconds depending on length
#   segments, info = model.transcribe(audio_data, language="zh")
#
#   # Step 3: Reject non-Mandarin audio to avoid false translations
#   if info.language != "zh":
#       logger.info(f"Non-Mandarin audio detected ({info.language}). Skipping.")
#       return None

## 5.3 Comment all config values with units and reason
#
# GOOD (in config.py):
#   # Silence duration (seconds) before mic recording stops.
#   # 1.5s feels natural — enough pause after a sentence.
#   # Too short (< 1s) cuts off speech; too long (> 3s) feels laggy.
#   SILENCE_THRESHOLD_SECONDS = 1.5
#
#   # Minimum recording length (seconds) to attempt transcription.
#   # Prevents sending tiny noise bursts to Whisper.
#   MIN_RECORDING_SECONDS = 0.5

## 5.4 Mark all external API calls clearly
# Any call to an external service (Whisper, Ollama, Qwen3-TTS,
# Twilio) must have a comment immediately above it:
#
#   # --- EXTERNAL CALL: Ollama / Qwen2.5 translation ---
#   response = requests.post(OLLAMA_URL, json=payload, timeout=30)
#   # --- END EXTERNAL CALL ---

## 5.5 No commented-out dead code
# If code is removed, delete it entirely. Do not leave blocks of
# commented-out code — it confuses debugging. Use git history instead.


# ─────────────────────────────────────────────────────────────
# SECTION 6 — ERROR HANDLING STANDARD
# ─────────────────────────────────────────────────────────────

## 6.1 Every external service call must be wrapped in try/except
#
# REQUIRED pattern for all service calls:
#
#   try:
#       response = requests.post(OLLAMA_URL, json=payload, timeout=30)
#       response.raise_for_status()
#   except requests.exceptions.ConnectionError:
#       # Ollama is not running or unreachable
#       logger.error(
#           "Cannot reach Ollama at %s\n"
#           "Fix: Make sure Ollama is running → run: ollama serve",
#           OLLAMA_URL
#       )
#       return None
#   except requests.exceptions.Timeout:
#       logger.error(
#           "Ollama took too long to respond (>30s).\n"
#           "Fix: The model may be loading — wait 30s and try again."
#       )
#       return None
#   except requests.exceptions.HTTPError as e:
#       logger.error("Ollama returned an error: %s", e)
#       return None

## 6.2 Never use bare `except:`
# Always catch specific exceptions. Bare `except:` hides bugs.
#
# BAD:   except:
# BAD:   except Exception:   (only use this as a last resort with a log)
# GOOD:  except requests.exceptions.ConnectionError:
# GOOD:  except FileNotFoundError:

## 6.3 Error messages must include a fix suggestion
# Every logger.error() message must end with:
# "Fix: [one sentence telling the owner what to do]"
#
# GOOD:
#   logger.error(
#       "Whisper model not found at %s\n"
#       "Fix: Run setup.sh to download the model.",
#       MODEL_PATH
#   )

## 6.4 Graceful degradation — never crash the whole pipeline
# If one service fails (e.g., TTS is down), the pipeline should
# log the error, skip that step, and continue running.
# The user should see a clear message, not a Python traceback.


# ─────────────────────────────────────────────────────────────
# SECTION 7 — LOGGING STANDARD
# ─────────────────────────────────────────────────────────────

## 7.1 Use the centralised logger, never print()
# All output goes through utils/logger.py.
# Never use bare print() statements in production code.
# (print() is allowed only in main.py for user-facing UI text.)
#
#   from utils.logger import get_logger
#   logger = get_logger(__name__)

## 7.2 Log every major pipeline step
# The owner must be able to watch the terminal and understand
# exactly what is happening at every moment.
#
# Required log points:
#   - When recording starts and stops
#   - When each service call begins and ends
#   - What language was detected
#   - What the translated text is (so owner can verify accuracy)
#   - When a WhatsApp message is sent successfully
#   - Any skipped step and why

## 7.3 Log format
# Format: [TIME] [LEVEL] [MODULE] — message
# Example:
#   [14:32:01] INFO  transcribe   — Recording started. Listening for Mandarin...
#   [14:32:05] INFO  transcribe   — Detected language: zh (confidence: 0.98)
#   [14:32:05] INFO  transcribe   — Transcript: 你今天吃饭了吗？
#   [14:32:06] INFO  translate    — Calling Ollama / Qwen2.5...
#   [14:32:07] INFO  translate    — Translation: "Did you eat today?"
#   [14:32:07] INFO  whatsapp     — Sending English message to +6591234567...
#   [14:32:08] INFO  whatsapp     — Message delivered. WhatsApp message ID: SM123

## 7.4 Log levels — use correctly
#   logger.debug()   → detailed internal state (disabled in production)
#   logger.info()    → normal pipeline steps (always visible)
#   logger.warning() → something unexpected but recoverable
#   logger.error()   → a step failed, pipeline continues
#   logger.critical()→ a step failed and the whole pipeline must stop


# ─────────────────────────────────────────────────────────────
# SECTION 8 — CONFIG AND SECRETS MANAGEMENT
# ─────────────────────────────────────────────────────────────

## 8.1 All settings live in config.py
# config.py is the single source of truth for all constants.
# It reads from the .env file for secrets.
# No file except config.py should ever read .env directly.
#
# config.py structure:
#
#   import os
#   from dotenv import load_dotenv
#   load_dotenv()
#
#   # ── Audio settings ──────────────────────────────────────
#   SAMPLE_RATE         = 16000   # Hz — required by Whisper
#   CHANNELS            = 1       # Mono — required by Whisper
#   SILENCE_THRESHOLD   = 1.5     # Seconds of silence to stop recording
#   MIN_RECORDING_SECS  = 0.5     # Ignore recordings shorter than this
#   TEMP_AUDIO_PATH     = "temp/input.wav"
#   REPLY_AUDIO_PATH    = "temp/reply.mp3"
#
#   # ── Whisper (local STT) ─────────────────────────────────
#   WHISPER_MODEL       = "large-v3"
#   WHISPER_DEVICE      = "cuda"   # Use "cpu" if ROCm fails
#   WHISPER_LANGUAGE    = "zh"     # Mandarin Chinese
#
#   # ── Ollama (local translation LLM) ──────────────────────
#   OLLAMA_URL          = "http://localhost:11434/api/generate"
#   OLLAMA_MODEL        = "qwen2.5:7b"
#   OLLAMA_TIMEOUT_SECS = 30
#
#   # ── Qwen3-TTS (local Mandarin TTS) ──────────────────────
#   TTS_URL             = "http://localhost:8880/v1/audio/speech"
#   TTS_VOICE           = "zh-female-warm"   # Change to preferred voice
#   TTS_TIMEOUT_SECS    = 20
#
#   # ── WhatsApp / Twilio ────────────────────────────────────
#   TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID")
#   TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN")
#   TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM")  # whatsapp:+14155238886
#   MY_WHATSAPP_NUMBER  = os.getenv("MY_WHATSAPP_NUMBER")     # whatsapp:+6591234567

## 8.2 .env.example must always be kept up to date
# Any new secret added to config.py must also appear in .env.example
# with a placeholder value and a comment explaining what it is.

## 8.3 Never log secret values
# logger calls must never include API keys, auth tokens, or phone numbers.
# Log only the fact that a credential was loaded, not its value:
#
# GOOD:  logger.info("Twilio credentials loaded successfully.")
# BAD:   logger.info(f"Using token: {TWILIO_AUTH_TOKEN}")


# ─────────────────────────────────────────────────────────────
# SECTION 9 — NAMING CONVENTIONS
# ─────────────────────────────────────────────────────────────

## 9.1 Files: lowercase_with_underscores.py
#   audio_capture.py    ✓
#   AudioCapture.py     ✗
#   audiocapture.py     ✗

## 9.2 Functions: lowercase_with_underscores
#   def capture_audio()         ✓
#   def captureAudio()          ✗
#   def CaptureAudio()          ✗

## 9.3 Variables: lowercase_with_underscores
#   audio_path = "..."          ✓
#   audioPath  = "..."          ✗

## 9.4 Constants (in config.py): UPPERCASE_WITH_UNDERSCORES
#   SAMPLE_RATE = 16000         ✓
#   sample_rate = 16000         ✗  (looks like a variable, not a constant)

## 9.5 Classes: PascalCase (only if a class is truly needed)
#   class AudioCapture:         ✓
#   class audio_capture:        ✗
#
#   NOTE: Prefer simple functions over classes.
#   Only create a class if you need to hold state across calls
#   (e.g., keeping a Whisper model loaded between recordings).

## 9.6 Be descriptive — no single-letter variables except loop counters
#   audio_file_path    ✓       (clear)
#   afp                ✗       (cryptic)
#   f                  ✗       (meaningless)
#   i                  ✓       (only in for loops: for i in range(...))


# ─────────────────────────────────────────────────────────────
# SECTION 10 — CODE SIMPLICITY RULES
# ─────────────────────────────────────────────────────────────

## 10.1 Maximum function length: 40 lines
# If a function is longer than 40 lines, split it.
# No exceptions. Long functions hide bugs.

## 10.2 Maximum nesting depth: 3 levels
# If you have if inside if inside if inside for → refactor.
# Use early returns to flatten logic:
#
# BAD (3 levels deep):
#   def process():
#       if audio:
#           if language == "zh":
#               if confidence > 0.8:
#                   return translate(audio)
#
# GOOD (flat with early returns):
#   def process():
#       if not audio:
#           return None
#       if language != "zh":
#           return None
#       if confidence <= 0.8:
#           return None
#       return translate(audio)

## 10.3 No one-liners that sacrifice readability
#
# BAD:
#   result = translate(transcribe(capture())) if mic_on else None
#
# GOOD:
#   if not mic_on:
#       return None
#   audio    = capture()
#   text     = transcribe(audio)
#   result   = translate(text)

## 10.4 No lambda functions except in simple sorted() / map() calls
# Lambdas are hard to debug. Use named functions.

## 10.5 Avoid list/dict comprehensions longer than one line
#
# BAD:
#   results = [translate(t) for t in transcripts if t and len(t) > 5 and is_mandarin(t)]
#
# GOOD:
#   results = []
#   for t in transcripts:
#       if t and len(t) > 5 and is_mandarin(t):
#           results.append(translate(t))

## 10.6 Type hints on all function signatures
# Every function must declare input and output types.
# This makes the code self-documenting and helps catch bugs.
#
#   def transcribe_audio(audio_path: str) -> str | None:
#   def send_whatsapp_text(message: str, to_number: str) -> bool:
#   def generate_mandarin_audio(text: str) -> bytes | None:


# ─────────────────────────────────────────────────────────────
# SECTION 11 — TESTING STANDARD
# ─────────────────────────────────────────────────────────────

## 11.1 One test file per service file
#   services/transcribe.py  →  tests/test_transcribe.py

## 11.2 Every test must have a plain English description
#
#   def test_transcribe_returns_none_for_non_mandarin_audio():
#       """
#       If we feed English audio to transcribe_audio(),
#       it should return None — not an English transcript.
#       This prevents English speech from being mis-translated.
#       """

## 11.3 Test both happy path and failure cases
# For every function, write:
#   - One test where everything works correctly
#   - One test where the input is wrong/missing
#   - One test where the external service is unavailable

## 11.4 Use mock for external services in tests
# Tests must never actually call Whisper, Ollama, Twilio, or TTS.
# Use unittest.mock to simulate their responses.
# Real service calls belong in manual integration tests only.

## 11.5 Keep tests simple and readable
# A test file should be readable by the project owner
# even if they don't know Python well.


# ─────────────────────────────────────────────────────────────
# SECTION 12 — HARDWARE-SPECIFIC RULES
# ─────────────────────────────────────────────────────────────

## 12.1 ACTIVE: MacBook M4 rules
#
# Issue: faster-whisper does not support Apple Metal GPU.
# Fix:   Always use device="cpu" on Mac. M4 CPU is fast enough.
#        Config: WHISPER_DEVICE = "cpu"
#
# Issue: Qwen3-TTS requires ROCm/CUDA Docker — not available on Mac.
# Fix:   Use Kokoro TTS (pip install kokoro) on Mac.
#        Fallback: subprocess.run(["say", "-v", "Ting-Ting", text])
#        Config: TTS_BACKEND = "kokoro"
#
# Issue: pyaudio needs PortAudio on Mac.
# Fix:   brew install portaudio before pip install pyaudio.
#
# Issue: Some Python packages lack Apple Silicon (arm64) wheels.
# Fix:   Check for native arm64 version before installing.
#        Never use Rosetta emulation for Python packages.

## 12.2 FUTURE: Brahma AMD ROCm rules (apply at migration time)
#
# Issue: Qwen3-TTS 5–10x slowdown on certain decode_window_frames values.
# Fix:   Always set decode_window_frames=72. Never use 64, 66, 67, 71, 80.
#
# Issue: ROCm uses HIP but faster-whisper expects "cuda" string.
# Fix:   Set device="cuda" — ROCm maps this automatically on AMD.
#
# Issue: First startup of Qwen3-TTS takes ~75 seconds (torch.compile).
# Fix:   Log "TTS warming up (~75s on first run)..." and use 120s timeout.

## 12.3 All models are LOCAL — never fall back to cloud APIs
# If a local service is unreachable, log the error and tell the
# owner which service to start. Never silently switch to OpenAI,
# Azure, or any cloud API as a fallback.
#
# Mac: if Ollama is unreachable → "Fix: run 'ollama serve' in a terminal"
# Mac: if Kokoro fails → fall back to macOS 'say' command only

## 12.4 All file paths use pathlib.Path
# Use relative paths inside the project.
# Use pathlib.Path() — never string concatenation.
#
# GOOD:  from pathlib import Path
#        audio_path = Path("temp") / "input.wav"
# BAD:   audio_path = "temp/" + "input.wav"

## 12.5 Audio device index
# Store as MIC_DEVICE_INDEX = None in config.py (None = system default).
# If recording fails or wrong mic is used, log:
# "Fix: run python utils/list_audio_devices.py to find your mic index,
#  then set MIC_DEVICE_INDEX in config.py"


# ─────────────────────────────────────────────────────────────
# SECTION 13 — GIT AND VERSION CONTROL
# ─────────────────────────────────────────────────────────────

## 13.1 .gitignore must include:
#   .env
#   temp/
#   __pycache__/
#   *.pyc
#   .venv/
#   *.mp3
#   *.wav

## 13.2 Commit message format:
#   [service] short description of what changed
#
#   Examples:
#   [transcribe] add silence detection before sending to Whisper
#   [config] add MIC_DEVICE_INDEX setting
#   [tts] fix ROCm decode_window_frames bug
#   [docs] update SKILL.md with new error handling rules

## 13.3 Never commit broken code
# Run python main.py --test before every commit to verify
# the pipeline starts without errors.


# ─────────────────────────────────────────────────────────────
# SECTION 14 — README.md REQUIREMENTS
# ─────────────────────────────────────────────────────────────

## README.md must contain:
#
#   1. What this project does (2-3 sentences, plain English)
#   2. System requirements (Ubuntu, AMD ROCm, Python version)
#   3. Step-by-step setup (numbered, copy-paste commands)
#   4. How to start each service (Ollama, Qwen3-TTS Docker, main.py)
#   5. How to use it (F key = forward, R key = reply, Q key = quit)
#   6. Troubleshooting table:
#      | Problem                        | Fix                              |
#      |--------------------------------|----------------------------------|
#      | No Mandarin detected           | Check mic index in config.py     |
#      | Ollama connection refused      | Run: ollama serve                |
#      | TTS taking too long            | Wait 75s on first run            |
#      | WhatsApp message not arriving  | Check Twilio sandbox approval    |
#
#   7. How to update .env with your own credentials


# ─────────────────────────────────────────────────────────────
# END OF SKILL.md
# ─────────────────────────────────────────────────────────────
# Last updated: 2026-05-23
# Project: LingoBridge — Ambient Family Language Bridge
# ─────────────────────────────────────────────────────────────
