# Massage Slot Monitor Bot

This bot watches [@GenesisMassagesBot](https://t.me/GenesisMassagesBot) on Telegram and **sends you a message the moment a massage slot with your specialist becomes available**. No more refreshing manually.

---

## What Does This Bot Do?

Imagine you want a massage with a specific specialist (e.g. "Anna"), but every time you open @GenesisMassagesBot all the slots are taken. This program runs on your computer (or a server), checks the bot every 60 seconds automatically, and sends you a Telegram notification the instant a slot opens up.

---

## Complete Setup Guide (Step by Step)

### Step 1: Install Python

Python is a programming language. This bot is written in Python, so you need it installed.

**Check if you already have it:**

Open a terminal (see below how), type this, and press Enter:

```
python3 --version
```

If you see something like `Python 3.10.12` or higher — great, skip to Step 2.

**If you don't have Python:**

- **Windows**: Go to [python.org/downloads](https://www.python.org/downloads/), click the big yellow "Download Python" button, run the installer. **IMPORTANT: check the box that says "Add Python to PATH"** before clicking Install.
- **Mac**: Go to [python.org/downloads](https://www.python.org/downloads/), download and install. Or if you have Homebrew, run `brew install python3`.
- **Linux (Ubuntu/Debian)**: Run `sudo apt update && sudo apt install python3 python3-pip`.

**What is a "terminal"?**

A terminal is a text window where you type commands.

- **Windows**: Press the Windows key, type `cmd`, and open "Command Prompt". Or search for "PowerShell".
- **Mac**: Open Finder, go to Applications > Utilities > Terminal.
- **Linux**: Press Ctrl+Alt+T, or find "Terminal" in your applications.

---

### Step 2: Download This Project

You need to get these files onto your computer.

**Option A — Download as a ZIP (easiest, no GitHub account needed):**

1. Go to [this project's GitHub page](https://github.com/volodymyrdontsov-oss/TGMASAGBOT)
2. Click the green **"Code"** button
3. Click **"Download ZIP"**
4. Find the downloaded ZIP file and extract (unzip) it to a folder you'll remember (e.g. your Desktop)
5. Open your terminal and navigate to that folder:

```
cd Desktop/TGMASAGBOT-main
```

(On Windows, replace `Desktop` with the actual path if different.)

**Option B — Using Git (if you want to try it):**

Git is a tool developers use to download and manage code. If you don't have it, skip to Option A.

```
git clone https://github.com/volodymyrdontsov-oss/TGMASAGBOT.git
cd TGMASAGBOT
```

---

### Step 3: Install the Bot's Dependencies

Dependencies are other pieces of software this bot needs to work. You install them with one command.

In your terminal, make sure you're inside the project folder (from Step 2), then run:

```
pip3 install -r requirements.txt
```

You should see some text scrolling by and ending with "Successfully installed ...". That means it worked.

> **If you get an error** like "pip3 not found", try `pip install -r requirements.txt` instead (without the "3").

---

### Step 4: Get Your Telegram API Credentials

The bot needs permission to use your Telegram account. You get this by registering an "app" with Telegram (it's free and takes 2 minutes).

1. Open your browser and go to: **[https://my.telegram.org/apps](https://my.telegram.org/apps)**
2. Enter your **phone number** (the one linked to your Telegram) and click "Next"
3. Telegram will send you a **code in the Telegram app** — enter it on the website
4. You'll see a form to create an application:
   - **App title**: type anything, e.g. `My Monitor`
   - **Short name**: type anything, e.g. `mymonitor`
   - **Platform**: choose any (e.g. "Desktop")
   - **Description**: leave empty or type anything
   - Click **"Create application"**
5. You'll now see a page with your app details. You need two values:
   - **`api_id`** — a number, e.g. `12345678`
   - **`api_hash`** — a long text/number combo, e.g. `a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4`

**Write these down or keep the page open — you'll need them in the next step.**

---

### Step 5: Configure the Bot

Now you need to tell the bot your credentials and which specialist to watch for.

1. In the project folder, find the file called `.env.example`
2. **Make a copy** of it and name the copy `.env` (just `.env`, no other name)

   - **Windows (Command Prompt)**: `copy .env.example .env`
   - **Mac/Linux (Terminal)**: `cp .env.example .env`

3. Open the `.env` file in any text editor (Notepad on Windows, TextEdit on Mac, or any editor you like)

4. Fill in the three required values:

```
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4
SPECIALIST_NAME=Anna
```

Replace the example values with:
- Your **actual api_id** from Step 4
- Your **actual api_hash** from Step 4
- The **name of the specialist** you want (e.g. `Anna`, `Maria`, etc.) — it matches even partial names, so `Ann` would match "Anna"

5. **Save the file** and close the editor.

> **About the other settings in the file:** You can leave them as they are. They have sensible defaults. `CHECK_INTERVAL=60` means the bot checks every 60 seconds — you can change this to `30` for faster checking.

---

### Step 6: Discover the Bot's Menu Structure

Before the monitor can work, it needs to know **which buttons to press** inside @GenesisMassagesBot to get to the specialist's schedule. Every Telegram booking bot has a different menu layout, so we need to map it out first.

Run this in your terminal (make sure you're in the project folder):

```
python3 -m src.discover --depth 2
```

**What will happen:**

1. The program will ask for your **phone number** — type it with country code (e.g. `+380501234567`) and press Enter
2. Telegram will send a **login code** to your Telegram app — type it and press Enter
3. It might ask for your **2FA password** if you have one set up — type it and press Enter
4. The program will now automatically open @GenesisMassagesBot, send `/start`, and press every button it finds, logging everything

**The output will look something like this** (your actual output will be different):

```
=== Starting bot flow discovery (depth=2) ===
BOT TEXT: Welcome! Choose an option:
  row 0: [ Book a massage | My bookings ]
  row 1: [ About us ]
-> Pressing button [Book a massage]
BOT TEXT: Choose a specialist:
  row 0: [ Anna | Maria ]
  row 1: [ Ivan | Back ]
...
```

**Read the output carefully** — it shows you the exact button names and menu structure. You'll need this for the next step.

> **Note:** After this first login, a session file is saved. You won't need to enter your phone number or code again.

---

### Step 7: Create the Button Sequence File

Now you need to create a file that tells the monitor exactly which buttons to press to reach your specialist's available slots.

1. Create a new file called **`flow_config.json`** in the project folder
2. Open it in a text editor

Based on what you saw in Step 6, write the sequence of button presses. For example, if the discovery showed:
- First you need to send `/start`
- Then press "Book a massage"
- Then press "Anna"

Your `flow_config.json` would look like this:

```json
[
    {"text": "/start"},
    {"button_text": "Book a massage"},
    {"button_text": "Anna"}
]
```

**Rules for this file:**

- The file must start with `[` and end with `]`
- Each step is inside `{ }` separated by commas
- `{"text": "/start"}` means "send this text to the bot"
- `{"button_text": "Book a massage"}` means "click the button that contains this text"
- The button text matching is case-insensitive (so `"anna"` matches a button labeled `"Anna"`)
- Use the exact button labels you saw in the discovery output
- **Save the file** when done

> **If you're not sure what to put here:** Share the output from Step 6 with me and I'll help you write this file.

---

### Step 8: Start the Monitor

Everything is configured. Now start the bot:

```
python3 -m src
```

**What you'll see:**

```
2026-03-17 12:00:00 [INFO] src.client: Logged in as YourName (id=123456)
2026-03-17 12:00:01 [INFO] src.monitor: Starting monitor – checking every 60s for specialist 'Anna'
2026-03-17 12:00:05 [INFO] src.monitor: No new slots found. Will check again in 60s.
```

The program will now keep running and checking. **When a slot is found**, you'll get a message in your Telegram **"Saved Messages"** chat that says something like:

> Available massage slots found!
> - Anna
>   12:00
>
> Open @GenesisMassagesBot to book now!

**To stop the monitor:** Press `Ctrl+C` in the terminal.

**To keep it running in the background:** Keep the terminal window open. If you close it, the monitor stops.

---

## Frequently Asked Questions

### "What are Saved Messages?"

Open Telegram, tap the search icon, and type "Saved Messages". It's a built-in chat with yourself — that's where notifications go by default.

### "Can I get notifications on my phone even if the bot runs on another computer?"

Yes! Set up a separate notification bot:

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the instructions to create a bot (give it any name)
3. BotFather will give you a **token** — a long string like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`
4. Open your new bot in Telegram and press **Start**
5. Search for **@userinfobot** in Telegram, send it any message — it will reply with your **chat ID** (a number)
6. Open your `.env` file and add:

```
NOTIFY_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
NOTIFY_CHAT_ID=987654321
```

Now you'll get push notifications from your custom bot.

### "The bot stopped working / the menu changed"

Re-run the discovery tool and update `flow_config.json`:

```
python3 -m src.discover --depth 2
```

### "I get a 'pip not found' error"

Try one of these instead:

```
pip install -r requirements.txt
python -m pip install -r requirements.txt
python3 -m pip install -r requirements.txt
```

### "I get a 'python3 not found' error"

Try just `python` instead of `python3`. On Windows, it's often just `python`.

### "Is this safe? Can I get banned?"

This uses your real Telegram account to interact with the bot — exactly the same way you would manually, just automated. Telegram generally doesn't ban accounts for interacting with bots at reasonable intervals. The default check interval (60 seconds) is very conservative. Don't set it below 15 seconds.

### "Can I run this 24/7?"

Yes, but your computer needs to stay on. For always-on monitoring, consider running it on a cheap VPS (Virtual Private Server) like a $5/month DigitalOcean droplet or a free-tier Oracle Cloud instance. If this is interesting, I can help you set it up.

---

## Security Notes

- The `.env` file contains your secret API credentials — **never share it** with anyone
- The `.session` file (created after first login) gives full access to your Telegram account — **keep it safe** and never share it
- Both files are listed in `.gitignore` so they won't accidentally be uploaded anywhere

---

## Quick Reference (For After Setup)

| What you want to do | Command |
|---|---|
| Start monitoring | `python3 -m src` |
| Re-discover bot menus | `python3 -m src.discover --depth 2` |
| Stop monitoring | Press `Ctrl+C` in the terminal |
| Change specialist / interval | Edit the `.env` file, then restart |
| Change button sequence | Edit `flow_config.json`, then restart |
