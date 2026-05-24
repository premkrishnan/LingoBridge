---
name: lingobridge-project-context
description: >
  Project context, architecture, hardware specs, service endpoints,
  pipeline design, and coding directives for LingoBridge.
  Claude Code MUST read this file at the start of every session.
  Currently developing on MacBook M4. Production target is Brahma (Ubuntu/AMD ROCm).
  Section 2 documents the active Mac environment. Section 2b documents Brahma for
  future migration. All code must be written Mac-first but structured to switch easily.
version: "1.1"
project: LingoBridge
dev_environment: macbook-m4
last_updated: "2026-05-23"
---

# CLAUDE.md — LingoBridge Project Context
# ============================================================
# This file tells Claude Code WHAT to build and WHY.
# The SKILL.md file tells Claude Code HOW to build it.
# Both files must be read before starting any coding task.
# ============================================================


# ─────────────────────────────────────────────────────────────
# ARCHITECTURE DECISION (FINAL)
# ─────────────────────────────────────────────────────────────
#
#   Single modular Python script — NOT multi-agent.
#
#   The pipeline is a linear sequence of 5 steps:
#   capture → transcribe → translate → TTS → deliver
#
#   Each step is a separate module in services/.
#   main.py calls them in sequence — no orchestration framework,
#   no LangChain, no CrewAI, no agent abstractions.
#
#   Why NOT multi-agent:
#   - Pipeline is linear, not parallel or branching
#   - No autonomous decision-making needed between steps
#   - Agent frameworks add latency — bad for real-time conversation
#   - Framework abstractions make debugging harder
#   - LingoBridge is a tool, not a research assistant
#
#   Why modular single script:
#   - Each service module is readable, testable, and swappable
#   - Errors are visible exactly at the step that fails
#   - Zero framework overhead — pure Python
#   - Easy to migrate to Brahma (just change config.py values)


# ─────────────────────────────────────────────────────────────
# SECTION 1 — WHAT IS LINGOBRIDGE?
# ─────────────────────────────────────────────────────────────

## Project name:   LingoBridge
## Tagline:        "Bridge the language gap, instantly."
## Form factor:    Small wearable clip — worn on collar or shirt pocket

## The problem it solves:
#   The owner speaks English. His mother-in-law (MIL) speaks
#   Mandarin Chinese only. They meet in person regularly but
#   cannot communicate directly. Phone-based translation apps
#   are too slow and require both parties to look at a screen.
#   LingoBridge makes face-to-face communication natural,
#   hands-free, and invisible.

## How it works — two directions:
#
#   FORWARD (Receiving — MIL to owner):
#   MIL speaks Mandarin near the clip
#     → Clip mic captures her voice
#     → Whisper transcribes Mandarin speech to text
#     → Qwen2.5 translates Mandarin text to English
#     → English message sent to owner's WhatsApp
#     → Owner reads it on his phone (like a normal WhatsApp message)
#
#   REVERSE (Replying — owner to MIL):
#   Owner presses reply button and speaks English to the clip
#     → Clip mic captures his voice
#     → Whisper transcribes English speech to text
#     → Qwen2.5 translates English text to Mandarin
#     → Qwen3-TTS generates a natural Mandarin voice audio file
#     → Mandarin audio sent to owner's WhatsApp as a voice note
#     → Owner plays the voice note from his phone speaker to MIL
#     → MIL hears natural spoken Mandarin

## Key design principles:
#   - Zero friction: no app to open, no button to hold (except reply)
#   - Always-on: clip listens continuously in forward mode
#   - Person-to-person: designed for face-to-face, not remote calls
#   - Local-first: all AI runs on Brahma server, no cloud APIs
#   - Privacy: no audio or conversation data leaves the home network
#   - Simplicity: MIL needs no device, no app, no training


# ─────────────────────────────────────────────────────────────
# SECTION 2 — ACTIVE DEV MACHINE: MACBOOK M4
# ─────────────────────────────────────────────────────────────

## *** CURRENT ENVIRONMENT — all code runs here during Phase 1 ***
## The MacBook M4 is the development and testing machine.
## All AI services run locally on the Mac via Ollama and faster-whisper.
## When Phase 1 is complete and tested, we migrate to Brahma (see Section 2b).

## Hardware specs:
#   Chip:     Apple M4 (ARM architecture)
#   RAM:      24 GB unified memory (shared CPU + GPU — no separate VRAM)
#   GPU:      Apple Metal (built into M4 — NOT CUDA, NOT ROCm)
#   OS:       macOS
#   Python:   Use Python 3.11+ via Homebrew or pyenv

## AI stack on Mac — install commands:
#   Ollama:          brew install ollama
#                    ollama pull qwen3:8b
#   faster-whisper:  pip install faster-whisper
#   Kokoro TTS:      pip install kokoro  (Mandarin-capable, runs on CPU)
#   pyaudio:         brew install portaudio && pip install pyaudio
#   python-dotenv:   pip install python-dotenv
#   twilio:          pip install twilio

## CRITICAL Mac M4 rules (apply in every relevant file):
#
#   1. faster-whisper device on Mac:
#      Use device="cpu" — Apple Metal is not supported by faster-whisper.
#      M4 CPU handles large-v3 in ~2–4s per sentence — fast enough.
#      Config: WHISPER_DEVICE = "cpu"
#      Migration note: change to "cuda" when switching to Brahma.
#
#   2. TTS backend on Mac — use Kokoro:
#      Qwen3-TTS requires ROCm/CUDA Docker — not available on Mac.
#      Primary:  Kokoro (pip install kokoro) — good Mandarin quality.
#      Fallback: macOS built-in TTS via subprocess:
#                subprocess.run(["say", "-v", "Ting-Ting", mandarin_text])
#                (Ting-Ting is macOS built-in Mandarin neural voice)
#      Config: TTS_BACKEND = "kokoro"  # Mac | change to "qwen3" on Brahma
#
#   3. No Docker needed on Mac for Phase 1:
#      Skip all Docker setup — that is Brahma-only for Qwen3-TTS.
#
#   4. Audio on Mac:
#      pyaudio works via PortAudio (Homebrew). MIC_DEVICE_INDEX = None
#      uses the system default mic. For external USB mic, run:
#      python utils/list_audio_devices.py to find the correct index.
#
#   5. ARM architecture:
#      All pip packages must have ARM/Apple Silicon wheels.
#      If a package fails to install, check for a native arm64 version.
#      Never use Rosetta emulation for Python packages.


# ─────────────────────────────────────────────────────────────
# SECTION 2b — FUTURE PRODUCTION MACHINE: BRAHMA (Ubuntu/ROCm)
# ─────────────────────────────────────────────────────────────

## *** NOT ACTIVE YET — migrate here after Phase 1 is working on Mac ***
## All notes preserved here so migration is a config change, not a rewrite.

## Hardware specs:
#   CPU:      AMD Ryzen 7700
#   RAM:      32 GB system memory
#   GPU:      AMD (16 GB VRAM)
#   GPU API:  ROCm (NOT CUDA — AMD-specific compute stack)
#   OS:       Ubuntu (Linux)

## Migration checklist — config.py values to change Mac → Brahma:
#
#   Setting                  Mac value     Brahma value
#   ──────────────────────   ──────────    ──────────────────────
#   WHISPER_DEVICE           "cpu"         "cuda"
#   TTS_BACKEND              "kokoro"      "qwen3"
#   TTS_URL                  (unused)      "http://localhost:8880/v1/audio/speech"
#   TTS_DECODE_WINDOW_FRAMES (unused)      72   ← CRITICAL: prevents ROCm slowdown
#   TTS_STARTUP_TIMEOUT      (unused)      120  ← first-run torch.compile warmup
#
## Brahma ROCm notes (apply at migration time):
#   - Qwen3-TTS: ALWAYS set decode_window_frames=72
#     (values 66, 67, 71 cause 5–10x slowdown — known ROCm upstream bug)
#   - Qwen3-TTS first startup: ~75s warmup — not a crash, log and wait
#   - faster-whisper: device="cuda" — ROCm auto-maps this on AMD GPU
#   - Start TTS: docker compose -f docker-compose.rocm.yml up -d


# ─────────────────────────────────────────────────────────────
# SECTION 3 — LOCAL SERVICE ENDPOINTS
# ─────────────────────────────────────────────────────────────

## All services run locally. Mac endpoints are active.
## Brahma endpoints shown for reference at migration time.
## All values live in config.py / .env — never hardcoded.

## Whisper (Speech-to-Text):
#   Library:  faster-whisper (called directly as a Python library, no HTTP)
#   Model:    large-v3
#   Device:   Mac → "cpu"  |  Brahma → "cuda"
#   Language: auto-detect; return None if detected language is not "zh"

## Ollama (Translation LLM):
#   URL:      http://localhost:11434/api/generate  (same on Mac and Brahma)
#   Model:    qwen3:8b  (upgrade to qwen3:14b if translation feels flat)
#   IMPORTANT: Always prefix every prompt with /no_think
#              Qwen3 reasoning mode adds 5-8s latency — /no_think disables it
#   Purpose:  Mandarin → English (forward) and English → Mandarin (reverse)
#   Timeout:  30 seconds per request

## TTS (Mandarin Text-to-Speech):
#   Mac:      Kokoro library (pip install kokoro) — called directly
#             Fallback: subprocess.run(["say", "-v", "Ting-Ting", text])
#   Brahma:   Qwen3-TTS HTTP at http://localhost:8880/v1/audio/speech
#   Output:   MP3 saved to temp/reply.mp3
#   Backend:  Controlled by TTS_BACKEND in config.py

## WhatsApp delivery (Twilio):
#   API:      Twilio WhatsApp Business API
#   Sandbox:  Used for development and testing (Mac and Brahma)
#   Sends:    Text messages (forward) and voice notes (reverse)
#   Creds:    Loaded from .env only — never hardcoded


# ─────────────────────────────────────────────────────────────
# SECTION 4 — PROJECT FILE STRUCTURE
# ─────────────────────────────────────────────────────────────

## lingobridge/
## │
## ├── SKILL.md                  ← Coding law (read first)
## ├── CLAUDE.md                 ← This file (project context)
## ├── README.md                 ← Human setup and usage guide
## ├── .env                      ← Secrets (never commit to git)
## ├── .env.example              ← Template with placeholder values
## ├── .gitignore                ← Must include .env, temp/, __pycache__/
## ├── config.py                 ← All settings and constants
## ├── main.py                   ← Entry point — runs the pipeline loop
## │
## ├── services/
## │   ├── __init__.py
## │   ├── audio_capture.py      ← Mic recording with silence detection
## │   ├── transcribe.py         ← Whisper STT (speech → Mandarin text)
## │   ├── translate.py          ← Ollama LLM (text → text, both directions)
## │   ├── tts.py                ← Qwen3-TTS (Mandarin text → audio file)
## │   └── whatsapp.py           ← Twilio send text + send voice note
## │
## ├── utils/
## │   ├── __init__.py
## │   ├── logger.py             ← Centralised logging (used by all modules)
## │   ├── audio_utils.py        ← WAV format conversion, silence detection
## │   └── list_audio_devices.py ← Helper: prints available mic devices
## │
## ├── tests/
## │   ├── test_audio_capture.py
## │   ├── test_transcribe.py
## │   ├── test_translate.py
## │   ├── test_tts.py
## │   └── test_whatsapp.py
## │
## └── temp/                     ← Auto-cleared temp audio files
##     └── .gitkeep

## EXACT FILE LIST — Claude Code must create every file below.
## This is the authoritative list. No file may be skipped.
## Use this list to verify with: find . -not -path './.git/*' -type f | sort
##
##   ./.env.example
##   ./.gitignore
##   ./config.py
##   ./main.py
##   ./README.md
##   ./services/__init__.py
##   ./services/audio_capture.py
##   ./services/transcribe.py
##   ./services/translate.py
##   ./services/tts.py
##   ./services/whatsapp.py
##   ./utils/__init__.py
##   ./utils/logger.py
##   ./utils/audio_utils.py
##   ./utils/list_audio_devices.py
##   ./tests/__init__.py
##   ./tests/test_audio_capture.py
##   ./tests/test_transcribe.py
##   ./tests/test_translate.py
##   ./tests/test_tts.py
##   ./tests/test_whatsapp.py
##   ./temp/.gitkeep


# ─────────────────────────────────────────────────────────────
# SECTION 5 — PIPELINE LOGIC
# ─────────────────────────────────────────────────────────────

## main.py runs a continuous loop with two modes.
## The loop must be clean and readable — no business logic in main.py.
## All logic lives in services/. main.py only calls service functions.

## FORWARD MODE (default — always listening):
#
#   while running:
#       audio_path  = capture_audio()           # wait for speech + silence
#       transcript  = transcribe_audio(audio_path)  # returns None if not Mandarin
#       if transcript is None: continue         # skip — not Mandarin speech
#       english     = translate_to_english(transcript)
#       send_whatsapp_text(english)
#       delete temp audio file

## REPLY MODE (triggered by pressing R key):
#
#   english_audio_path = capture_audio()        # record owner's English reply
#   english_text       = transcribe_audio(english_audio_path)
#   mandarin_text      = translate_to_mandarin(english_text)
#   audio_path         = generate_mandarin_audio(mandarin_text)
#   send_whatsapp_voice_note(audio_path)
#   delete temp audio files

## KEYBOARD CONTROLS in main.py:
#   R key → switch to reply mode for one recording, then back to forward
#   Q key → quit gracefully (log shutdown, clean up temp files)
#   Any other key → ignored

## PIPELINE RULES:
#   - If any service returns None, log the reason and skip that cycle
#   - Never crash the loop — catch all errors per service
#   - Always delete temp audio files after each cycle (privacy)
#   - Print a simple status line to terminal each cycle:
#     "[FORWARD] Listening for MIL..."
#     "[FORWARD] Heard: 你今天吃饭了吗？ → Did you eat today?"
#     "[REPLY]   Recording your reply..."
#     "[REPLY]   Sent Mandarin audio to WhatsApp."


# ─────────────────────────────────────────────────────────────
# SECTION 6 — CONFIG.PY STRUCTURE
# ─────────────────────────────────────────────────────────────

## config.py is the single source of truth for all settings.
## Claude Code must keep config.py updated whenever a new
## setting, path, model name, or constant is introduced.

## Required sections in config.py:
#
#   # ── Project ──────────────────────────────────────────────
#   PROJECT_NAME    = "LingoBridge"
#   VERSION         = "0.1.0"
#
#   # ── Audio ────────────────────────────────────────────────
#   SAMPLE_RATE             = 16000   # Hz — Whisper requires 16kHz
#   CHANNELS                = 1       # Mono — Whisper requires mono
#   SILENCE_THRESHOLD_SECS  = 1.5     # Seconds of silence → stop recording
#   MIN_RECORDING_SECS      = 0.5     # Ignore recordings shorter than this
#   MIC_DEVICE_INDEX        = None    # None = system default mic
#   TEMP_INPUT_AUDIO        = "temp/input.wav"
#   TEMP_REPLY_AUDIO        = "temp/reply.mp3"
#
#   # ── Whisper (local STT on Brahma) ─────────────────────────
#   WHISPER_MODEL           = "large-v3"
#   WHISPER_DEVICE          = "cuda"   # ROCm auto-maps on AMD GPU
#   WHISPER_COMPUTE_TYPE    = "float16"
#   MANDARIN_LANGUAGE_CODE  = "zh"
#
#   # ── Ollama / Qwen3 (local translation — Mac and Brahma) ──────
#   OLLAMA_BASE_URL         = "http://localhost:11434"
#   OLLAMA_API_URL          = "http://localhost:11434/api/generate"
#   OLLAMA_MODEL            = "qwen3:8b"    # upgrade to qwen3:14b if needed
#   OLLAMA_TIMEOUT_SECS     = 30
#
#   # ── Qwen3-TTS (local Mandarin TTS on Brahma) ──────────────
#   TTS_API_URL             = "http://localhost:8880/v1/audio/speech"
#   TTS_VOICE               = "zh-female-warm"
#   TTS_TIMEOUT_SECS        = 20
#   TTS_STARTUP_TIMEOUT     = 120    # Longer for first-run torch.compile
#   TTS_DECODE_WINDOW_FRAMES = 72    # CRITICAL: prevents ROCm slowdown bug
#
#   # ── WhatsApp / Twilio ─────────────────────────────────────
#   TWILIO_ACCOUNT_SID      = os.getenv("TWILIO_ACCOUNT_SID")
#   TWILIO_AUTH_TOKEN       = os.getenv("TWILIO_AUTH_TOKEN")
#   TWILIO_WHATSAPP_FROM    = os.getenv("TWILIO_WHATSAPP_FROM")
#   MY_WHATSAPP_NUMBER      = os.getenv("MY_WHATSAPP_NUMBER")


# ─────────────────────────────────────────────────────────────
# SECTION 7 — TRANSLATION PROMPT DESIGN
# ─────────────────────────────────────────────────────────────

## The Ollama translation prompts are critical to quality.
## These are the exact prompt templates to use in translate.py.
##
## CRITICAL — /no_think prefix:
##   Qwen3 has a built-in reasoning/thinking mode that deliberates
##   before answering. For translation it adds 5-8 seconds of latency
##   with no quality benefit. The /no_think tag at the START of the
##   prompt disables it entirely, giving 1-2 second responses.
##   EVERY prompt sent to Qwen3 must start with /no_think.

## Forward prompt (Mandarin → English):
#
#   TRANSLATE_TO_ENGLISH_PROMPT = """
#   /no_think
#   You are translating a spoken message from a Chinese mother-in-law
#   to her English-speaking son-in-law. The conversation is personal,
#   warm, and family-oriented — not formal or business language.
#
#   Translate the following Mandarin Chinese text into natural,
#   conversational English. Keep the tone warm and natural.
#   Preserve questions as questions. Do not add explanations.
#   Return only the translated English text, nothing else.
#
#   Mandarin text: {mandarin_text}
#   """

## Reverse prompt (English → Mandarin):
#
#   TRANSLATE_TO_MANDARIN_PROMPT = """
#   /no_think
#   You are translating a spoken message from an English-speaking
#   son-in-law to his Chinese mother-in-law. The conversation is
#   personal, warm, and family-oriented.
#
#   Translate the following English text into natural, conversational
#   Simplified Mandarin Chinese (普通话). Use respectful but warm
#   language appropriate for speaking to an elder family member.
#   Do not add pinyin. Return only the Mandarin Chinese text, nothing else.
#
#   English text: {english_text}
#   """

## IMPORTANT: Store these prompt templates in config.py as
## multiline strings. Never hardcode them inside translate.py.


# ─────────────────────────────────────────────────────────────
# SECTION 8 — .ENV FILE REQUIREMENTS
# ─────────────────────────────────────────────────────────────

## Required .env variables (copy to .env.example with placeholders):
#
#   # Twilio WhatsApp credentials
#   # Get from: https://console.twilio.com
#   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
#   TWILIO_AUTH_TOKEN=your_auth_token_here
#
#   # Twilio sandbox WhatsApp number (format: whatsapp:+14155238886)
#   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
#
#   # Your personal WhatsApp number (format: whatsapp:+6591234567)
#   MY_WHATSAPP_NUMBER=whatsapp:+your_number_here

## .env rules:
#   - .env is NEVER committed to git
#   - .env.example IS committed (with placeholder values only)
#   - config.py is the ONLY file that reads from .env
#   - All other files import constants from config.py


# ─────────────────────────────────────────────────────────────
# SECTION 9 — CODING STANDARDS REFERENCE
# ─────────────────────────────────────────────────────────────

## Full coding standards are in SKILL.md.
## This section is a quick-reference summary only.

## Claude Code MUST follow ALL rules in SKILL.md including:
#   - File header format (every .py file)
#   - Function docstring format (every function)
#   - Inline commenting style (WHY not WHAT)
#   - Error handling with human-readable "Fix:" messages
#   - Centralised logging via utils/logger.py (no bare print())
#   - All constants in config.py (no magic values in code)
#   - Type hints on all function signatures
#   - Maximum 40 lines per function
#   - Maximum 3 levels of nesting
#   - Naming conventions (snake_case functions, UPPER_CASE constants)
#   - No cloud API fallbacks — local only


# ─────────────────────────────────────────────────────────────
# SECTION 10 — DEVELOPMENT PHASES
# ─────────────────────────────────────────────────────────────

## Phase 1 — Software MVP (current phase — MacBook M4):
#   Hardware:   MacBook M4 acts as the "clip" during development
#   Goal:       Full pipeline working end-to-end on the Mac
#   AI stack:   Ollama (Qwen3 8B) + faster-whisper + Kokoro TTS
#   Success:    Owner can receive MIL's Mandarin as WhatsApp English,
#               and play back a Mandarin voice note to MIL
#   Milestone:  Tested in a real face-to-face conversation with MIL
#   Next:       Migrate config to Brahma — should be < 1 hour of changes

## Phase 2 — Raspberry Pi wearable:
#   Hardware:   Raspberry Pi Zero 2W + microphone module
#   Goal:       Same pipeline running on a clip-sized device
#   Notes:      Pi sends audio to Brahma over Wi-Fi; Brahma does all AI

## Phase 3 — Custom PCB + companion app:
#   Hardware:   Custom-designed PCB, proper clip enclosure
#   Goal:       Consumer-ready form factor
#   Notes:      App for device setup, voice selection, contact config


# ─────────────────────────────────────────────────────────────
# SECTION 11 — WHAT CLAUDE CODE SHOULD NEVER DO
# ─────────────────────────────────────────────────────────────

## These are hard rules — never violate them regardless of task:
#
#   1. Never use cloud AI APIs (OpenAI, Azure, Google, Anthropic)
#      as primary services or fallbacks. Everything runs on Brahma.
#
#   2. Never store audio files beyond the current pipeline cycle.
#      Delete temp/input.wav and temp/reply.mp3 after each run.
#
#   3. Never log or print Twilio credentials, auth tokens,
#      or the owner's phone number.
#
#   4. Never add a dependency without checking platform compatibility.
#      On Mac: must have ARM/Apple Silicon wheels (no Rosetta for Python).
#      On Brahma: must have ROCm support — CUDA-only libs will fail silently.
#      Always verify before adding a new pip dependency.
#
#   5. Never put business logic in main.py.
#      main.py only imports from services/ and calls their functions.
#
#   6. Never create a service file that imports from another service.
#      Services are independent. Shared code goes in utils/ only.
#
#   7. Never skip writing the file header and function docstrings.
#      Every file and every function must be documented per SKILL.md.


# ─────────────────────────────────────────────────────────────
# END OF CLAUDE.md
# ─────────────────────────────────────────────────────────────
# Project:      LingoBridge
# Version:      0.1.0
# Last updated: 2026-05-23
# Owner:        Personal project — family language bridge device
# ─────────────────────────────────────────────────────────────
