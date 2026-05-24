---
name: lingobridge-session-prompts
description: >
  Exact word-for-word prompts for each Claude Code / Pi coding session.
  These prompts are deliberately explicit and self-contained.
  Do not reference "see Section X" — all instructions are inline.
  One prompt per session. Wait for completion before starting next.
version: "1.0"
project: LingoBridge
last_updated: "2026-05-23"
---

# PROMPTS.md — LingoBridge Session Prompts
# ============================================================
# Copy each prompt exactly as written into Claude Code or Pi.
# Do not paraphrase or shorten them.
# Paste the agent's output back to the architect (Claude.ai chat)
# for review before starting the next session.
# ============================================================


# ─────────────────────────────────────────────────────────────
# SESSION 1 — Project skeleton
# ─────────────────────────────────────────────────────────────

Read CLAUDE.md and SKILL.md before doing anything.

Create the following files exactly as listed below.
All files are empty except for the SKILL.md file header block.
Do not write any logic, imports, or functions yet.

Create these files:

  .env.example
  .gitignore
  config.py
  main.py
  README.md
  services/__init__.py
  services/audio_capture.py
  services/transcribe.py
  services/translate.py
  services/tts.py
  services/whatsapp.py
  utils/__init__.py
  utils/logger.py
  utils/audio_utils.py
  utils/list_audio_devices.py
  tests/__init__.py
  tests/test_audio_capture.py
  tests/test_transcribe.py
  tests/test_translate.py
  tests/test_tts.py
  tests/test_whatsapp.py
  temp/.gitkeep

.gitignore must contain:
  .env
  temp/
  __pycache__/
  *.pyc
  .venv/
  *.mp3
  *.wav

.env.example must contain:
  TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  TWILIO_AUTH_TOKEN=your_auth_token_here
  TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
  MY_WHATSAPP_NUMBER=whatsapp:+your_number_here

After creating all files, run:
  find . -not -path './.git/*' -type f | sort

Every file in the list above must appear in the output.
Do not proceed until all files are confirmed present.


# ─────────────────────────────────────────────────────────────
# SESSION 2 — config.py and utils/logger.py
# ─────────────────────────────────────────────────────────────

Read CLAUDE.md and SKILL.md before doing anything.

Write config.py with the following exact content and structure.
Follow ALL rules in SKILL.md: file header, inline comments
explaining WHY, no magic values.

config.py must contain these sections in this order:

SECTION 1 — File header (SKILL.md format)
SECTION 2 — Imports (os, pathlib.Path, dotenv)
SECTION 3 — Project identity constants:
  PROJECT_NAME = "LingoBridge"
  VERSION = "0.1.0"

SECTION 4 — Audio settings with comments:
  SAMPLE_RATE = 16000        # Whisper requires exactly 16kHz
  CHANNELS = 1               # Whisper requires mono
  SILENCE_THRESHOLD_SECS = 1.5
  MIN_RECORDING_SECS = 0.5
  MIC_DEVICE_INDEX = None    # None = system default
  TEMP_INPUT_AUDIO = Path("temp") / "input.wav"
  TEMP_REPLY_AUDIO = Path("temp") / "reply.mp3"

SECTION 5 — Whisper settings:
  WHISPER_MODEL = "large-v3"
  WHISPER_DEVICE = "cpu"     # Mac: "cpu" | Brahma: "cuda"
  WHISPER_COMPUTE_TYPE = "float16"
  MANDARIN_LANGUAGE_CODE = "zh"

SECTION 6 — Ollama / Qwen3 settings:
  OLLAMA_API_URL = "http://localhost:11434/api/generate"
  OLLAMA_MODEL = "qwen3:8b"  # upgrade to qwen3:14b if needed
  OLLAMA_TIMEOUT_SECS = 30

SECTION 7 — TTS settings:
  TTS_BACKEND = "kokoro"     # Mac: "kokoro" | Brahma: "qwen3"
  TTS_URL = "http://localhost:8880/v1/audio/speech"  # Brahma only
  TTS_VOICE = "zh-female-warm"
  TTS_TIMEOUT_SECS = 20
  TTS_STARTUP_TIMEOUT = 120
  TTS_DECODE_WINDOW_FRAMES = 72  # CRITICAL: prevents ROCm slowdown

SECTION 8 — WhatsApp / Twilio (load from .env):
  TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
  TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
  TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM")
  MY_WHATSAPP_NUMBER = os.getenv("MY_WHATSAPP_NUMBER")

SECTION 9 — Translation prompts (multiline strings):
  TRANSLATE_TO_ENGLISH_PROMPT — includes /no_think prefix,
    warm family tone instruction, Mandarin input placeholder
  TRANSLATE_TO_MANDARIN_PROMPT — includes /no_think prefix,
    respectful elder tone, Simplified Mandarin output,
    English input placeholder

---

Then write utils/logger.py with:
- File header (SKILL.md format)
- get_logger(name) function that returns a configured logger
- Format: [HH:MM:SS] LEVEL  module_name — message
- Handlers: StreamHandler (console) only for now
- Default level: INFO
- Docstring on get_logger explaining args, returns, example usage


# ─────────────────────────────────────────────────────────────
# SESSION 3 — services/audio_capture.py + utils/audio_utils.py
# ─────────────────────────────────────────────────────────────

Read CLAUDE.md and SKILL.md before doing anything.

Write services/audio_capture.py with:
- File header (SKILL.md format)
- Import from config: SAMPLE_RATE, CHANNELS, SILENCE_THRESHOLD_SECS,
  MIN_RECORDING_SECS, MIC_DEVICE_INDEX, TEMP_INPUT_AUDIO
- Import get_logger from utils.logger
- One class AudioCapture with:
    __init__: loads config values, initialises logger
    capture_audio() -> str | None:
      Records from mic until SILENCE_THRESHOLD_SECS of silence.
      Returns path to saved WAV file, or None if recording too short.
      Logs: "Listening for speech...", "Speech detected",
            "Silence detected — processing", "Recording too short, skipping"
- try/except on all pyaudio calls with Fix: messages
- Comment explaining WHY silence threshold is 1.5s

Write utils/audio_utils.py with:
- File header (SKILL.md format)
- is_silent(audio_chunk, threshold) -> bool
  Checks if an audio chunk is below silence threshold
- save_wav(audio_data, path, sample_rate, channels) -> bool
  Saves raw audio bytes to WAV file using wave module
- Docstrings and inline comments on both functions

Write utils/list_audio_devices.py with:
- File header (SKILL.md format)
- Script that when run prints all available audio input devices
  with their index number and name
- If run directly (if __name__ == "__main__") prints devices
- Instructions at the top: "Run this if mic is not detected.
  Copy the index number to MIC_DEVICE_INDEX in config.py"


# ─────────────────────────────────────────────────────────────
# SESSION 4 — services/transcribe.py
# ─────────────────────────────────────────────────────────────

Read CLAUDE.md and SKILL.md before doing anything.

Write services/transcribe.py with:
- File header (SKILL.md format)
- Import from config: WHISPER_MODEL, WHISPER_DEVICE,
  WHISPER_COMPUTE_TYPE, MANDARIN_LANGUAGE_CODE
- Import get_logger from utils.logger
- One class Transcriber with:
    __init__: loads faster-whisper model, logs model loading,
      handles model load failure gracefully
    transcribe_audio(audio_path: str) -> str | None:
      Step 1: Check audio file exists — return None if not
      Step 2: Run Whisper transcription
      Step 3: Check detected language == "zh" — return None if not
      Step 4: Join segments and return transcript string
      Logs: detected language + confidence, transcript text,
            or reason for returning None
- try/except on Whisper call with Fix: message
- Comment: WHY device="cpu" on Mac (Apple Metal not supported)
- Comment: WHY we reject non-Mandarin (prevents mis-translation)


# ─────────────────────────────────────────────────────────────
# SESSION 5 — services/translate.py
# ─────────────────────────────────────────────────────────────

Read CLAUDE.md and SKILL.md before doing anything.

Write services/translate.py with:
- File header (SKILL.md format)
- Import from config: OLLAMA_API_URL, OLLAMA_MODEL,
  OLLAMA_TIMEOUT_SECS, TRANSLATE_TO_ENGLISH_PROMPT,
  TRANSLATE_TO_MANDARIN_PROMPT
- Import get_logger from utils.logger
- Two functions:

translate_to_english(mandarin_text: str) -> str | None:
  Step 1: Format TRANSLATE_TO_ENGLISH_PROMPT with mandarin_text
  Step 2: POST to OLLAMA_API_URL with stream=False
  Step 3: Extract response text
  Step 4: Return English translation
  Log: "Calling Ollama...", "Translation: [result]"

translate_to_mandarin(english_text: str) -> str | None:
  Same structure as above using TRANSLATE_TO_MANDARIN_PROMPT

Both functions must have:
- try/except ConnectionError with Fix: "run ollama serve"
- try/except Timeout with Fix: "model may be loading, wait 30s"
- try/except HTTPError with error details
- Comment: WHY /no_think prefix is critical for response speed


# ─────────────────────────────────────────────────────────────
# SESSION 6 — services/tts.py
# ─────────────────────────────────────────────────────────────

Read CLAUDE.md and SKILL.md before doing anything.

Write services/tts.py with:
- File header (SKILL.md format)
- Import from config: TTS_BACKEND, TTS_VOICE, TEMP_REPLY_AUDIO
- Import get_logger from utils.logger
- One function:

generate_mandarin_audio(mandarin_text: str) -> str | None:
  Step 1: Check TTS_BACKEND value
  Step 2a: If "kokoro" — use Kokoro library to generate audio,
           save to TEMP_REPLY_AUDIO, return path
  Step 2b: If "say" fallback — use subprocess:
           subprocess.run(["say", "-v", "Ting-Ting", "-o",
           str(TEMP_REPLY_AUDIO), mandarin_text])
           return path
  Step 3: If neither works, log error and return None
  Log: which backend was used, output file path

- Comment: WHY macOS "say -v Ting-Ting" is the fallback
  (Ting-Ting is macOS built-in Mandarin neural voice)
- try/except on Kokoro import with automatic fallback to "say"
- try/except on subprocess call


# ─────────────────────────────────────────────────────────────
# SESSION 7 — services/whatsapp.py
# ─────────────────────────────────────────────────────────────

Read CLAUDE.md and SKILL.md before doing anything.

Write services/whatsapp.py with:
- File header (SKILL.md format)
- Import from config: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
  TWILIO_WHATSAPP_FROM, MY_WHATSAPP_NUMBER
- Import get_logger from utils.logger
- Two functions:

send_text_message(message: str) -> bool:
  Sends English translation as WhatsApp text to MY_WHATSAPP_NUMBER
  Returns True on success, False on failure
  Logs: "Sending WhatsApp message...", "Delivered: [message_sid]"
  Never logs credential values — only success/failure status

send_voice_note(audio_path: str) -> bool:
  Sends Mandarin AIFF as WhatsApp voice note to MY_WHATSAPP_NUMBER
  Returns True on success, False on failure
  Logs: "Sending voice note...", "Voice note delivered"

Both functions:
- Check credentials are not None before calling Twilio
  Fix: "add credentials to .env file"
- try/except TwilioRestException with human-readable Fix message
- Comment: WHY we never log credential values


# ─────────────────────────────────────────────────────────────
# SESSION 8 — main.py
# ─────────────────────────────────────────────────────────────

Read CLAUDE.md and SKILL.md before doing anything.

Write main.py with:
- File header (SKILL.md format)
- Imports from all services and utils
- Import get_logger from utils.logger
- Two pipeline functions:

forward_pipeline() -> None:
  Step 1: audio_path = capture_audio()
  Step 2: if audio_path is None → return
  Step 3: transcript = transcribe_audio(audio_path)
  Step 4: if transcript is None → delete audio_path, return
  Step 5: english = translate_to_english(transcript)
  Step 6: if english is None → delete audio_path, return
  Step 7: send_text_message(english)
  Step 8: delete audio_path (privacy — never store audio)
  Print: "[FORWARD] Heard: [transcript] → [english]"

reply_pipeline() -> None:
  Step 1: Print "[REPLY] Recording your English reply..."
  Step 2: audio_path = capture_audio()
  Step 3: if audio_path is None → return
  Step 4: english = transcribe_audio(audio_path)
  Step 5: mandarin = translate_to_mandarin(english)
  Step 6: Send mandarin via send_mandarin_text(mandarin)
  Step 7: Also play audio locally: afplay temp/reply.aiff
           via subprocess so MIL hears it directly
  Step 8: delete audio files (privacy)
  Print: "[REPLY] Mandarin sent to WhatsApp + played aloud."

main loop:
  Print startup banner:
    "================================"
    " LingoBridge v0.1.0 — Running  "
    "================================"
    "Listening for Mandarin..."
    "Controls: R = reply | Q = quit"
  
  Use pynput.keyboard.Listener for non-blocking key detection
  R key → call reply_pipeline()
  Q key → quit gracefully, print "LingoBridge stopped."
  Default → call forward_pipeline() continuously
  Wrap in try/except KeyboardInterrupt for clean Ctrl+C exit

- No business logic in main.py — only calls to service functions
- Comment: WHY audio files deleted after every cycle (privacy)
- Comment: WHY we use pynput (non-blocking — doesn't interrupt 
  the mic capture loop)

# ─────────────────────────────────────────────────────────────
# SESSION 8 — main.py
# ─────────────────────────────────────────────────────────────

Read CLAUDE.md and SKILL.md before doing anything.

Add TELEGRAM_BOT_TOKEN to .env.example:
  TELEGRAM_BOT_TOKEN=8860491743:AAH975Oiusi4oO6aeO59VK264WVwfa9udw4

Add to config.py:
  # ── Telegram Bot ─────────────────────────────────────────
  # Token from @BotFather. Loaded from .env — never hardcoded.
  TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

Install dependency:
  pip install python-telegram-bot

Write services/bot.py with:
- File header (SKILL.md format)
- Imports: python-telegram-bot, config, transcribe, translate, tts
- Import get_logger from utils.logger
- Use Transcriber singleton (same pattern as main.py)

Commands and handlers:

/start → Reply:
  "🌉 LingoBridge is ready.
  Send a voice message to translate Mandarin → English.
  Or type /reply to record your English reply."

/help → Reply:
  "Commands:
  🎙 Send voice message → translates Mandarin to English
  /reply → record your English reply in Mandarin
  /stop → stop the bot"

Voice message handler (forward flow):
  Step 1: Bot receives voice message from user
  Step 2: Download the .ogg audio file to temp/input.ogg
  Step 3: Convert .ogg to .wav using ffmpeg OR pydub
          If neither available: try direct faster-whisper on .ogg
          (faster-whisper handles .ogg natively)
  Step 4: Transcribe with Transcriber.transcribe_audio()
  Step 5: If None → reply "⚠️ No Mandarin detected. Try again."
  Step 6: Translate with translate_to_english()
  Step 7: Reply to user with:
          "她说 (She said):
          🇨🇳 [mandarin transcript]
          🇬🇧 [english translation]"
  Step 8: Show two inline buttons:
          [✅ Reply in Mandarin] [🔄 Try again]

/reply command OR "Reply in Mandarin" button handler:
  Step 1: Ask user: "🎙 Send a voice message with your 
          English reply."
  Step 2: Wait for next voice message
  Step 3: Download .ogg → convert/pass to Whisper
  Step 4: Transcribe English text
  Step 5: Translate to Mandarin with translate_to_mandarin()
  Step 6: Generate audio with generate_mandarin_audio()
  Step 7: Send the .aiff file as a voice message back to user
  Step 8: Also send text:
          "Your reply in Mandarin:
          🇨🇳 [mandarin text]
          👆 Play this to MIL"

"Try again" button handler:
  → Delete last message, prompt user to send voice again

/stop → Reply "LingoBridge stopped." and stop polling

Main entry point (if __name__ == "__main__"):
  - Load TELEGRAM_BOT_TOKEN from config
  - Check token is not None — Fix: "add TELEGRAM_BOT_TOKEN to .env"
  - Use Application.builder().token().build()
  - Register all handlers
  - Log: "LingoBridge bot started — waiting for messages..."
  - app.run_polling()

Conversation state management:
  - Use ConversationHandler to track whether bot is waiting
    for MIL voice, or waiting for your English reply
  - States: WAITING_FOR_MIL, WAITING_FOR_REPLY

Error handling:
  - All Telegram API calls in try/except with Fix: messages
  - If translation fails → send user "⚠️ Translation failed. 
    Try again." — never crash the bot

Important notes:
  - Telegram voice messages arrive as .ogg format
  - faster-whisper can transcribe .ogg directly — no conversion needed
  - Send audio reply using: context.bot.send_voice()
  - Delete temp files after each exchange (privacy)
  - Log every step per SKILL.md Section 7
  - Never log the bot token value
  - bot.py replaces main.py as the entry point
  - All existing services (transcribe, translate, tts) are 
    called directly — no changes to those files
    
