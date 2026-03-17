# Massage Slot Monitor Bot

Monitors [@GenesisMassagesBot](https://t.me/GenesisMassagesBot) on Telegram for available massage slots with a specific specialist and sends you a notification the moment one appears.

## How It Works

The monitor uses a **Telegram userbot** (your own account via Telethon) to periodically interact with @GenesisMassagesBot, navigate its menus, and check for open time slots. When a slot matching your specialist is found, you get a Telegram notification instantly.

```
┌──────────────┐       ┌───────────────────────┐       ┌──────────────┐
│  Your Telegram│──────▶│  @GenesisMassagesBot  │──────▶│  Parse slots │
│  account      │  asks │  (booking bot)        │ reply │  & detect    │
└──────────────┘       └───────────────────────┘       │  availability│
                                                        └──────┬───────┘
                                                               │ found!
                                                        ┌──────▼───────┐
                                                        │  Notify you  │
                                                        │  via Telegram│
                                                        └──────────────┘
```

## Prerequisites

- **Python 3.10+**
- A **Telegram account** (the one you normally use, or a spare one)
- **Telegram API credentials** (`api_id` and `api_hash`)

## Quick Start

### 1. Get Telegram API Credentials

1. Go to [https://my.telegram.org/apps](https://my.telegram.org/apps)
2. Log in with your phone number
3. Create a new application (any name/description is fine)
4. Copy the `api_id` (a number) and `api_hash` (a hex string)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_API_ID` | Yes | Your Telegram API ID (number) |
| `TELEGRAM_API_HASH` | Yes | Your Telegram API hash (hex string) |
| `SPECIALIST_NAME` | Yes | Name of the specialist to watch for (case-insensitive substring match) |
| `CHECK_INTERVAL` | No | Seconds between checks (default: `60`) |
| `MASSAGE_BOT_USERNAME` | No | Bot username without @ (default: `GenesisMassagesBot`) |
| `SESSION_NAME` | No | Session file name (default: `massage_monitor_session`) |
| `NOTIFY_BOT_TOKEN` | No | Separate bot token for push notifications |
| `NOTIFY_CHAT_ID` | No | Chat ID to send push notifications to |

### 4. Discover the Bot's Menu Flow

Before monitoring, you need to map the bot's conversation flow so the monitor knows which buttons to press to reach the specialist schedule.

```bash
python -m src.discover --depth 2
```

On the first run you will be prompted for your **phone number** and a **login code** sent to your Telegram. A session file is saved locally so you won't be asked again.

The output shows every message, button label, and callback data the bot sends. Use this to build `flow_config.json`.

### 5. Create `flow_config.json`

Based on the discovery output, create a file called `flow_config.json` in the project root. It should be a JSON array of steps the monitor will follow each cycle:

```json
[
    {"text": "/start"},
    {"button_text": "Book massage"},
    {"button_text": "Choose specialist"},
    {"button_text": "Anna"}
]
```

Each step is one of:

| Step type | Example | Description |
|---|---|---|
| Send text | `{"text": "/start"}` | Send a text message to the bot |
| Click by label | `{"button_text": "Book"}` | Click the first button whose label contains this string (case-insensitive) |
| Click by data | `{"button_data": "aabbcc"}` | Click button with this exact callback data (hex-encoded) |

### 6. Start Monitoring

```bash
python -m src
```

The monitor will check every `CHECK_INTERVAL` seconds and send a message to your **Saved Messages** when a slot appears.

## Notification Options

### Saved Messages (default)

No extra setup needed. Notifications go to your Telegram "Saved Messages" chat.

### Separate Bot (optional)

For push notifications to your phone even when the monitor account differs from your daily account:

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Send `/start` to your new bot
3. Get your chat ID (send a message to [@userinfobot](https://t.me/userinfobot))
4. Set `NOTIFY_BOT_TOKEN` and `NOTIFY_CHAT_ID` in `.env`

## Project Structure

```
├── .env.example           # Environment variable template
├── flow_config.json       # Button sequence to reach specialist slots (you create this)
├── requirements.txt       # Python dependencies
├── src/
│   ├── __init__.py
│   ├── __main__.py        # Entry point: python -m src
│   ├── bot_interaction.py # Bot menu navigation & slot parsing
│   ├── client.py          # Telethon client setup
│   ├── config.py          # Configuration from environment
│   ├── discover.py        # Interactive flow discovery tool
│   ├── monitor.py         # Main monitoring loop
│   └── notifier.py        # Notification delivery
```

## Tips

- **Start with a short `CHECK_INTERVAL`** (e.g. 30s) during peak times, and increase it during off-hours to avoid rate limits.
- **Run on a server or always-on machine** (VPS, Raspberry Pi, etc.) so it monitors 24/7.
- The first run of `discover` or the monitor will ask for your phone number interactively. After that the session file handles authentication automatically.
- If the bot's menu structure changes, re-run `python -m src.discover` and update `flow_config.json`.

## Security Notes

- Your `.env` file and `*.session` files contain sensitive credentials. They are in `.gitignore` and should **never** be committed.
- The Telegram session file gives full access to your account. Keep it safe.
