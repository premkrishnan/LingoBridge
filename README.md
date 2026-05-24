# 🌉 LingoBridge (Updated until Phase 1)

**Real-time Mandarin ↔ English translation for face-to-face family conversations.**

LingoBridge is a Telegram bot that lets you have natural conversations with a Mandarin-speaking family member — no translator, no typing in Chinese, no apps needed on their side. You speak English, they hear Mandarin. They speak Mandarin, you read English.

---

## How It Works

**Forward (receiving):** Your family member speaks Mandarin near your phone → LingoBridge transcribes and translates → you receive the English text on Telegram.

**Reverse (replying):** You send an English voice message on Telegram → LingoBridge translates → you receive a Mandarin voice note to play to them.

```
MIL speaks Mandarin
       ↓
  Whisper STT (speech → text)
       ↓
  Qwen3:14b (Mandarin → English)
       ↓
  English text → your Telegram

You speak English into Telegram
       ↓
  Whisper STT (speech → text)
       ↓
  Qwen3:14b (English → Mandarin)
       ↓
  Tingting TTS (text → Mandarin audio)
       ↓
  Mandarin voice note → your Telegram → play to MIL
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Speech-to-text | Whisper large-v3 (faster-whisper) |
| Translation | Qwen3:14b via Ollama |
| Text-to-speech | macOS Tingting voice (afconvert → M4A) |
| Bot interface | Telegram (python-telegram-bot) |
| Fallback delivery | Twilio WhatsApp API |
| Dev hardware | MacBook M4 24GB, macOS Tahoe |
| Production target | Brahma server (AMD Ryzen 7700, 16GB VRAM, ROCm) |

---

## Requirements

- macOS (tested on macOS Tahoe / macOS 16)
- Python 3.13+
- [Ollama](https://ollama.com) installed and running
- Telegram account + bot token from [@BotFather](https://t.me/BotFather)
- Twilio account (optional — WhatsApp fallback only)
- Homebrew

---

## Installation

### 1. Clone the repository

```bash
git clone git@github.com:premkrishnan/LingoBridge.git
cd LingoBridge
```

### 2. Install system dependencies

```bash
brew install portaudio
```

### 3. Create and activate virtual environment

```bash
python3 -m venv lingob_env
source lingob_env/bin/activate
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 5. Install and set up Ollama

```bash
brew install ollama
ollama pull qwen3:14b
```

### 6. Download Whisper model

This happens automatically on first run. To pre-download:

```bash
python3 -c "
from faster_whisper import WhisperModel
print('Downloading large-v3 — takes a few minutes...')
WhisperModel('large-v3', device='cpu', compute_type='int8')
print('Done.')
"
```

### 7. Install Mandarin voice (macOS)

1. Open **System Settings → Accessibility → Read & Speak**
2. Click **System Voice → Manage Voices**
3. Find **Chinese (China mainland)** → download **Tingting**
4. Verify: `say -v Tingting "你好"`

### 8. Create your .env file

```bash
cp .env.example .env
nano .env
```

Fill in your credentials:

```
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
MY_WHATSAPP_NUMBER=whatsapp:+your_number
```

---

## Usage

### Start Ollama (required before running the bot)

```bash
# Pre-warm the model to avoid 60s cold start
ollama serve &
ollama run qwen3:14b "ready"
```

### Run LingoBridge

```bash
source lingob_env/bin/activate
python services/bot.py
```

### Telegram commands

| Command | Action |
|---|---|
| `/start` | Show welcome message and instructions |
| `/begin` | Start a translation session — bot begins listening |
| `/end` | End the session — bot stops listening |
| `/reply` | Switch to reply mode — send your English voice reply |
| `/help` | Show all commands |
| `/stop` | Stop the bot |

### Typical conversation flow

```
1. Sit down with MIL
2. Open Telegram → your LingoBridge bot
3. Type /begin
4. Hold phone toward MIL — record her speaking Mandarin
5. Send the voice message
6. Read the English translation
7. Tap [✅ Reply in Mandarin]
8. Record your English reply
9. Receive Mandarin voice note — tap play, face phone toward MIL
10. She hears your reply in Mandarin
11. Type /end when conversation is finished
```

---

## Finding Your Microphone Index

If the wrong microphone is being used:

```bash
python3 utils/list_audio_devices.py
```

Update `MIC_DEVICE_INDEX` in `config.py` with the correct index.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Ollama connection refused` | Run: `ollama serve` |
| Translation takes 60+ seconds | Pre-warm: `ollama run qwen3:14b "ready"` |
| `No Mandarin detected` | Speak clearly for 2+ seconds, hold phone closer |
| `Timed out` downloading voice | Bot retries automatically — check internet connection |
| `Tingting voice not found` | Install via System Settings → Accessibility → Read & Speak |
| Wrong microphone capturing | Run `python3 utils/list_audio_devices.py`, update `MIC_DEVICE_INDEX` |
| WhatsApp message not arriving | Check Twilio sandbox is joined and `.env` credentials are correct |
| `Module not found` error | Run `source lingob_env/bin/activate` before starting |

---

## Project Structure

```
LingoBridge/
├── config.py                 ← All settings and constants
├── main.py                   ← Terminal pipeline (alternative entry point)
├── services/
│   ├── bot.py                ← Telegram bot (main entry point)
│   ├── audio_capture.py      ← Microphone recording
│   ├── transcribe.py         ← Whisper speech-to-text
│   ├── translate.py          ← Qwen3 translation (both directions)
│   ├── tts.py                ← Mandarin text-to-speech
│   └── whatsapp.py           ← Twilio WhatsApp fallback
├── utils/
│   ├── logger.py             ← Centralised logging
│   ├── audio_utils.py        ← Audio processing helpers
│   └── list_audio_devices.py ← Microphone troubleshooting tool
├── tests/                    ← Unit tests (one per service)
├── CLAUDE.md                 ← Project context for AI coding agents
├── SKILL.md                  ← Coding standards for AI coding agents
├── PROMPTS.md                ← Session prompts used to build the project
├── .env.example              ← Credentials template
└── requirements.txt          ← Python dependencies
```

---

## Migrating to Brahma (Phase 2)

When moving from MacBook M4 to the Brahma Ubuntu/ROCm server, change these values in `config.py`:

| Setting | Mac value | Brahma value |
|---|---|---|
| `WHISPER_DEVICE` | `"cpu"` | `"cuda"` |
| `TTS_BACKEND` | `"say"` | `"qwen3"` |
| `OLLAMA_MODEL` | `"qwen3:14b"` | `"qwen3:14b"` |
| `TTS_DECODE_WINDOW_FRAMES` | (unused) | `72` |

Start Qwen3-TTS on Brahma:
```bash
docker compose -f docker-compose.rocm.yml up -d
```

---

## Roadmap

- [x] **Phase 1** — MacBook M4 + Telegram bot (complete)
- [ ] **Phase 2A** — Fix translation latency (auto Ollama warmup)
- [ ] **Phase 2B** — MIL-side Telegram bot (she initiates conversations)
- [ ] **Phase 2C** — Migrate to Brahma (GPU inference, Qwen3-TTS)
- [ ] **Phase 3** — Raspberry Pi wearable clip
- [ ] **Phase 4** — Custom PCB + enclosure

---

## Origin Story

LingoBridge was born from a simple problem — the owner speaks English, his mother-in-law speaks only Mandarin. They meet in person regularly but couldn't communicate directly. Designed as a wearable clip concept, Phase 1 is a Telegram bot that proves the core translation pipeline works. The clip hardware comes later.

---

## License

Personal project — not licensed for redistribution.
