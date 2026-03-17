# Massage Slot Monitor Bot

This bot watches [@GenesisMassagesBot](https://t.me/GenesisMassagesBot) on Telegram and **sends you a message the moment a massage slot with your specialist becomes available**. No more refreshing manually.

---

## What Does This Bot Do?

Imagine you want a massage with a specific specialist (e.g. "Anna"), but every time you open @GenesisMassagesBot all the slots are taken. This program checks the bot every 60 seconds automatically, and sends you a Telegram notification the instant a slot opens up.

You can run it on your own computer, but ideally you run it on a **server** (like Hetzner) so it works **24/7** even when your computer is off.

---

## Choose Your Setup Path

| | Local Machine | Hetzner Server (Recommended) |
|---|---|---|
| Runs 24/7? | Only while your computer is on | Yes, always |
| Survives restarts? | No | Yes (auto-starts) |
| Cost | Free | ~3.29 EUR/month |
| Difficulty | Easier | A few more steps, but this guide covers everything |

**Recommended:** Use a Hetzner server. It costs almost nothing, runs non-stop, and this guide walks you through every click.

---

## Part 1: Get Your Telegram API Credentials (Do This First, Regardless of Setup Path)

Before anything else, you need to get two secret codes from Telegram. This is free and takes 2 minutes.

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

**Write these down or keep the page open — you'll need them soon.**

---

## Part 2A: Set Up on a Hetzner Server (Recommended for 24/7)

This section walks you through renting a tiny server from Hetzner and setting everything up on it. If you've never used a server before, don't worry — just follow each step exactly.

### Step 1: Create a Hetzner Account

1. Go to **[https://www.hetzner.com/cloud](https://www.hetzner.com/cloud)**
2. Click **"Sign Up"** or **"Get Started"**
3. Create an account with your email, verify it, and add a payment method (credit card or PayPal)

### Step 2: Create a Server

1. Log into Hetzner Cloud Console at **[https://console.hetzner.cloud](https://console.hetzner.cloud)**
2. Click **"New project"** — name it anything (e.g. "Massage Bot") — then click into the project
3. Click **"Add Server"**
4. Configure the server:
   - **Location**: pick the one closest to you (e.g. "Falkenstein" or "Helsinki")
   - **Image (operating system)**: choose **Ubuntu 24.04**
   - **Type**: pick the cheapest one — **CX22** (2 vCPU, 4GB RAM) at ~4.35 EUR/month, or **CX11/CAX11** if available for cheaper. Any of the cheapest options is more than enough.
   - **Networking**: leave defaults
   - **SSH Key**: this is how you'll connect to the server securely. You have two options:

**Option A — Use a password (simpler for beginners):**

Skip the SSH key section. After clicking "Create", Hetzner will email you the root password.

**Option B — Use an SSH key (more secure):**

If you don't know what an SSH key is, use Option A. Otherwise:

On your computer, open a terminal and run:

```
ssh-keygen -t ed25519
```

Press Enter for all prompts (default location, no passphrase is fine). Then show the public key:

- **Mac/Linux**: `cat ~/.ssh/id_ed25519.pub`
- **Windows (PowerShell)**: `type $env:USERPROFILE\.ssh\id_ed25519.pub`

Copy the entire output (starts with `ssh-ed25519`), paste it into the "SSH Key" field on Hetzner, and give it a name.

5. Click **"Create & Buy Now"**
6. Wait about 30 seconds. Your server is created. You'll see its **IP address** on the dashboard — a number like `168.119.xxx.xxx`. **Copy this IP address.**

### Step 3: Connect to Your Server

Now you need to connect to the server from your computer. You do this through a "terminal" using a program called SSH.

**What is a "terminal"?** A text window where you type commands.

- **Windows**: Press the Windows key, type `cmd`, and open "Command Prompt". Or use "PowerShell".
- **Mac**: Open Finder > Applications > Utilities > Terminal.
- **Linux**: Press Ctrl+Alt+T.

In your terminal, type (replace `YOUR_IP` with the IP address from Step 2):

```
ssh root@YOUR_IP
```

For example: `ssh root@168.119.42.100`

- If it asks "Are you sure you want to continue connecting?" — type `yes` and press Enter
- If you used a password (Option A), type the password Hetzner emailed you and press Enter (the password won't show as you type — that's normal)
- If you used an SSH key (Option B), it connects automatically

**You are now connected to the server.** Everything you type from now on runs on the server, not on your computer. You'll see something like `root@ubuntu:~#`.

### Step 4: Set Up the Server

Now run these commands one at a time on the server. Copy each line, paste it into the terminal, and press Enter.

**4a. Update the server and install Python:**

```
apt update && apt install -y python3 python3-pip python3-venv git
```

This installs Python (the language the bot is written in) and Git (a tool to download the code). It may take a minute.

**4b. Create a dedicated user (so the bot doesn't run as root):**

```
adduser --disabled-password --gecos "" monitor
```

This creates a user called "monitor". Now switch to that user:

```
su - monitor
```

Your prompt changes to `monitor@ubuntu:~$`. Good.

**4c. Download the bot code:**

```
git clone https://github.com/volodymyrdontsov-oss/TGMASAGBOT.git
cd TGMASAGBOT
```

**4d. Set up a Python virtual environment and install dependencies:**

A virtual environment is like a clean room where the bot's software lives without interfering with anything else.

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

You'll see "Successfully installed ..." at the end. Your prompt now shows `(venv)` at the beginning — that means the virtual environment is active.

### Step 5: Configure the Bot on the Server

**5a. Create the config file:**

```
cp .env.example .env
nano .env
```

`nano` is a simple text editor that works in the terminal. You'll see the file contents.

**5b. Edit the values:**

Use the arrow keys to move around. Change these three lines to your actual values:

```
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4
SPECIALIST_NAME=Anna
```

**5c. Save and exit nano:**

1. Press **Ctrl+O** (the letter O, not zero) — this means "save"
2. Press **Enter** to confirm the filename
3. Press **Ctrl+X** to exit the editor

### Step 6: Discover the Bot's Menu Structure

Before the monitor can work, it needs to know **which buttons to press** inside @GenesisMassagesBot. Run the discovery tool:

```
python3 -m src.discover --depth 2
```

**What will happen:**

1. It asks for your **phone number** — type it with country code (e.g. `+380501234567`) and press Enter
2. Telegram sends a **login code** to your Telegram app — type it and press Enter
3. If you have **2FA** set up, type your password and press Enter
4. The tool walks through the bot's menus and prints everything it finds

**The output will look something like this** (yours will be different):

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

**Read the output carefully** — you need the exact button names for the next step.

> After this first login, a session file is saved. You won't need to enter your phone/code again.

### Step 7: Create the Button Sequence File

Based on what you saw in Step 6, create a file that tells the monitor which buttons to press:

```
nano flow_config.json
```

Type in the button sequence. For example, if the discovery showed that you need to send `/start`, then press "Book a massage", then press "Anna":

```json
[
    {"text": "/start"},
    {"button_text": "Book a massage"},
    {"button_text": "Anna"}
]
```

**Rules for this file:**

- The file must start with `[` and end with `]`
- Each step is inside `{ }`, separated by commas
- `{"text": "/start"}` means "send this text to the bot"
- `{"button_text": "Book a massage"}` means "click the button whose label contains this text"
- Button matching is case-insensitive (`"anna"` matches "Anna")
- Use the exact button labels from the discovery output

Save and exit: **Ctrl+O**, **Enter**, **Ctrl+X**.

> **If you're not sure what to put here:** Share the output from Step 6 with me and I'll write this file for you.

### Step 8: Test the Bot

Before setting up 24/7 operation, test that everything works:

```
python3 -m src
```

You should see logs like:

```
[INFO] src.client: Logged in as YourName (id=123456)
[INFO] src.monitor: Starting monitor – checking every 60s for specialist 'Anna'
[INFO] src.monitor: No new slots found. Will check again in 60s.
```

If you see this, it's working. Press **Ctrl+C** to stop it for now.

### Step 9: Set Up 24/7 Operation (systemd)

Now we'll make the bot run automatically in the background, restart if it crashes, and start on server reboot.

**9a. Go back to the root user:**

```
exit
```

Your prompt changes back to `root@ubuntu:~#`.

**9b. Create the service file:**

```
cp /home/monitor/TGMASAGBOT/massage-monitor.service /etc/systemd/system/massage-monitor.service
```

**9c. Update the service to use the virtual environment:**

```
nano /etc/systemd/system/massage-monitor.service
```

Change the `ExecStart` line to use the Python from the virtual environment:

```
ExecStart=/home/monitor/TGMASAGBOT/venv/bin/python3 -m src
```

Save and exit (**Ctrl+O**, **Enter**, **Ctrl+X**).

**9d. Enable and start the service:**

```
systemctl daemon-reload
systemctl enable massage-monitor
systemctl start massage-monitor
```

That's it. The bot is now running 24/7.

### Step 10: Verify It's Running

```
systemctl status massage-monitor
```

You should see green text saying **"active (running)"**. To see the live logs:

```
journalctl -u massage-monitor -f
```

Press **Ctrl+C** to stop watching logs (the bot keeps running).

### You're Done!

The bot is now monitoring @GenesisMassagesBot around the clock. When a slot opens for your specialist, you'll get a notification in your Telegram **"Saved Messages"**.

You can now close the terminal — the bot keeps running on the server.

---

## Part 2B: Set Up on Your Local Computer (Alternative)

If you prefer to run the bot on your own computer (it only works while your computer is on and the terminal is open):

### Step 1: Install Python

Python is the programming language this bot uses.

**Check if you already have it** — open a terminal and run:

```
python3 --version
```

If you see `Python 3.10.12` or higher, skip to Step 2.

**If you don't have Python:**

- **Windows**: Go to [python.org/downloads](https://www.python.org/downloads/), click "Download Python", run the installer. **IMPORTANT: check "Add Python to PATH"** before clicking Install.
- **Mac**: Go to [python.org/downloads](https://www.python.org/downloads/), download and install.
- **Linux**: Run `sudo apt update && sudo apt install python3 python3-pip`.

**What is a "terminal"?** A text window where you type commands.

- **Windows**: Press the Windows key, type `cmd`, and open "Command Prompt".
- **Mac**: Open Finder > Applications > Utilities > Terminal.
- **Linux**: Press Ctrl+Alt+T.

### Step 2: Download the Project

**Option A — Download as a ZIP (easiest):**

1. Go to [this project on GitHub](https://github.com/volodymyrdontsov-oss/TGMASAGBOT)
2. Click the green **"Code"** button, then **"Download ZIP"**
3. Extract the ZIP to a folder (e.g. your Desktop)
4. Open your terminal and navigate to it:

```
cd Desktop/TGMASAGBOT-main
```

**Option B — Using Git:**

```
git clone https://github.com/volodymyrdontsov-oss/TGMASAGBOT.git
cd TGMASAGBOT
```

### Step 3: Install Dependencies

```
pip3 install -r requirements.txt
```

> If you get "pip3 not found", try `pip install -r requirements.txt` or `python3 -m pip install -r requirements.txt`.

### Step 4: Configure

```
cp .env.example .env
```

(On Windows: `copy .env.example .env`)

Open `.env` in any text editor (Notepad, TextEdit, etc.) and fill in:

```
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4
SPECIALIST_NAME=Anna
```

Replace with your actual values from Part 1. Save the file.

### Step 5: Discover the Bot's Menus

```
python3 -m src.discover --depth 2
```

First time: enter your phone number and the login code Telegram sends you. Read the output to see the button names.

### Step 6: Create `flow_config.json`

Create a file called `flow_config.json` with the button sequence (see Part 2A Step 7 for details and format).

### Step 7: Start the Monitor

```
python3 -m src
```

Keep the terminal open. Press **Ctrl+C** to stop. The bot only runs while the terminal is open and your computer is on.

---

## Managing Your Server

Once the bot is running on your Hetzner server, here are common tasks:

### Connect to the Server

```
ssh root@YOUR_IP
```

### Check if the Bot is Running

```
systemctl status massage-monitor
```

### View Live Logs

```
journalctl -u massage-monitor -f
```

(Press Ctrl+C to stop watching — the bot continues running)

### View Recent Logs

```
journalctl -u massage-monitor --since "1 hour ago"
```

### Stop the Bot

```
systemctl stop massage-monitor
```

### Start the Bot Again

```
systemctl start massage-monitor
```

### Restart the Bot (After Changing Config)

If you changed `.env` or `flow_config.json`:

```
systemctl restart massage-monitor
```

### Change the Specialist or Check Interval

```
su - monitor
cd TGMASAGBOT
nano .env
```

Edit the values, save (**Ctrl+O**, **Enter**, **Ctrl+X**), then:

```
exit
systemctl restart massage-monitor
```

### Update the Bot Code (When New Versions Are Released)

```
su - monitor
cd TGMASAGBOT
source venv/bin/activate
git pull
pip install -r requirements.txt
exit
systemctl restart massage-monitor
```

---

## Notification Options

### Saved Messages (Default)

No setup needed. Notifications appear in your Telegram "Saved Messages" chat.

**How to find Saved Messages:** Open Telegram, tap the search icon, and type "Saved Messages".

### Separate Notification Bot (Optional)

If you want push notifications from a separate bot (useful if the monitor uses a different Telegram account):

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts to create a bot (any name)
3. BotFather gives you a **token** — looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`
4. Open your new bot in Telegram and press **Start**
5. Search for **@userinfobot** in Telegram, send it any message — it replies with your **chat ID** (a number)
6. Edit your `.env` file and add:

```
NOTIFY_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
NOTIFY_CHAT_ID=987654321
```

If on a server, restart: `systemctl restart massage-monitor`

---

## Frequently Asked Questions

### "Is this safe? Can I get banned?"

This uses your real Telegram account to interact with the bot — exactly the same way you would manually, just automated. Telegram generally doesn't ban accounts for interacting with bots at reasonable intervals. The default check interval (60 seconds) is very conservative. Don't set it below 15 seconds.

### "How much does the Hetzner server cost?"

The cheapest option is around 3-5 EUR/month. You can delete the server anytime to stop charges.

### "I lost connection to the server / my terminal closed"

Don't worry — the bot keeps running on the server. Just reconnect with `ssh root@YOUR_IP`.

### "The bot stopped working / the menu changed"

Connect to your server and re-run discovery:

```
ssh root@YOUR_IP
su - monitor
cd TGMASAGBOT
source venv/bin/activate
python3 -m src.discover --depth 2
nano flow_config.json
exit
systemctl restart massage-monitor
```

### "I get a 'python3 not found' error"

Try just `python` instead of `python3`. On Windows it's often just `python`.

---

## Security Notes

- The `.env` file contains your secret API credentials — **never share it** with anyone
- The `.session` file (created after first login) gives full access to your Telegram account — **keep it safe**
- Both files are in `.gitignore` so they won't accidentally be uploaded
- On a server, only the `monitor` user can access these files

---

## Quick Reference

| What you want to do | Command |
|---|---|
| Start monitoring (local) | `python3 -m src` |
| Start monitoring (server) | `systemctl start massage-monitor` |
| Stop monitoring (local) | Press `Ctrl+C` |
| Stop monitoring (server) | `systemctl stop massage-monitor` |
| Restart after config change (server) | `systemctl restart massage-monitor` |
| View logs (server) | `journalctl -u massage-monitor -f` |
| Check status (server) | `systemctl status massage-monitor` |
| Re-discover bot menus | `python3 -m src.discover --depth 2` |
| Change specialist / interval | Edit `.env`, then restart |
| Change button sequence | Edit `flow_config.json`, then restart |
