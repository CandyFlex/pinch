# Pinch

**Know your limits before they know you.**

![Windows](https://img.shields.io/badge/Windows-0078D4?style=flat&logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

A tiny Windows taskbar widget that monitors your Claude subscription usage in real-time. Never hit your rate limit mid-conversation again.

---

## What It Does

- **Taskbar pill** shows your 5-hour utilization and weekly usage at a glance, color-coded green/yellow/red, with a live countdown to your next reset
- **Click to expand** a detailed popup with all metrics: 5-hour rolling, 7-day Opus, 7-day Sonnet, extra usage credits, progress bars, and reset timers
- **System tray icon** with a crab claw that changes color to reflect your most urgent limit

Zero telemetry. No accounts. No backend. Just a single `.exe` that reads your usage and shows it.

---

## Quick Start

Pinch works with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — it reads your existing OAuth session automatically.

1. Download `Pinch.exe` from [Releases](../../releases)
2. Run it
3. Done

Pinch detects `~/.claude/.credentials.json` on launch. If Claude Code isn't installed, the setup wizard will let you know.

---

## Screenshots

### Taskbar Pill
The pill sits on your taskbar, left of the system tray. Shows utilization percentage, a live reset countdown, and weekly usage — all color-coded.

![Taskbar Pill](docs/screenshots/hero.png)

### Detail Popup
Click the pill to see the full breakdown — all rate limit buckets with progress bars and reset timers.

![Detail Popup](docs/screenshots/popup.png)

### Settings
Right-click the tray icon and choose "Settings..." to adjust polling interval and startup behavior.

![Settings](docs/screenshots/settings.png)

---

## Settings

Access from the system tray right-click menu → **Settings...**

- **Poll Interval**: How often to check usage (15s / 30s / 60s / 2 min)
- **Start with Windows**: Launch Pinch automatically on login
- **Test Connection**: Verify your OAuth token is working

Settings stored in `%LOCALAPPDATA%/Pinch/settings.json` — only display preferences, no credentials.

---

## How It Works

1. Reads your OAuth token from `~/.claude/.credentials.json` (written by Claude Code)
2. Polls `api.anthropic.com/api/oauth/usage` at your configured interval
3. Parses 5-hour rolling, 7-day Opus, 7-day Sonnet, and extra usage buckets
4. Renders a color-coded pill on the taskbar and a detail popup on click
5. Token is read fresh each poll and never stored — it goes out of scope immediately

### Security Model

- **No credentials stored** — OAuth token is read live from Claude Code's file each poll
- **No API keys** — OAuth only, no secrets to manage
- **No telemetry** — zero network calls except to `api.anthropic.com`
- **No backend** — everything runs locally
- **Settings file** contains only display preferences (poll interval, autostart)
- **TLS 1.2 minimum** enforced on all API connections
- **Certificate pinning** via bundled certifi CA bundle

---

## Technical Details

| Detail | Value |
|--------|-------|
| Language | Python 3.10+ |
| UI Framework | tkinter (stdlib) |
| Tray Icon | pystray + Pillow |
| Executable Size | ~30 MB (PyInstaller onefile) |
| Runtime Dependencies | 3 (pystray, Pillow, certifi) |
| Telemetry | None |
| Network | Anthropic API only |
| Data Storage | Local display preferences only |

---

## Building from Source

```bash
git clone https://github.com/DarkCandyLord/pinch.git
cd pinch
pip install -r requirements.txt

# Run directly
python -m pinch

# Test your connection
python -m pinch --test-api

# Build the exe
build.bat
# Output: dist/Pinch.exe
```

### Requirements

- Python 3.10+
- Windows 10/11
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated

---

## Why "Pinch"?

Because crabs pinch, claws grip, and you should know when you're about to get clamped by your rate limits. Also it's small — it pinches onto your taskbar.

---

## License

MIT License. See [LICENSE](LICENSE).

---

<p align="center">
  <a href="https://github.com/DarkCandyLord">
    <img src="https://img.shields.io/badge/More_Tools-DarkCandyLord-e06c75?style=for-the-badge" alt="DarkCandyLord" />
  </a>
</p>
