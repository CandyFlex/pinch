<p align="center">
  <img src="docs/screenshots/banner.png" alt="Don't Get Caught in a Pinch" width="100%" />
</p>

<h1 align="center">Pinch</h1>
<p align="center"><strong>Know your limits before they know you.</strong></p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-0078D4?style=flat-square&logo=windows&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" />
  <img src="https://img.shields.io/badge/Telemetry-Zero-brightgreen?style=flat-square" />
</p>

---

Ever been mid-conversation with Claude and suddenly hit a rate limit wall? That sinking "please try again later" feeling when you're deep in a coding session?

**Pinch fixes that.** It's a tiny taskbar widget that watches your Claude usage in real-time so you always know exactly where you stand.

---

## See It in Action

### Your taskbar, at a glance
A compact pill sits right on your taskbar showing your current utilization, a live countdown to your next reset, and weekly usage. Green means go. Yellow means slow down. Red means stop and wait.

<p align="center">
  <img src="docs/screenshots/hero.png" alt="Taskbar Pill" />
</p>

### Click for the full picture
One click expands a detailed popup with every metric that matters: 5-hour rolling, 7-day Opus, 7-day Sonnet, extra usage credits — each with progress bars and reset timers.

<p align="center">
  <img src="docs/screenshots/popup.png" alt="Detail Popup" width="300" />
</p>

### Tweak it your way
Right-click the tray icon for settings. Adjust your polling speed, set it to launch with Windows, or test your connection.

<p align="center">
  <img src="docs/screenshots/settings.png" alt="Settings" width="360" />
</p>

---

## Get Started in 30 Seconds

You need [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed. That's it.

```
1. Download Pinch.exe from Releases  -->  (link below)
2. Double-click it.
3. Done.
```

Pinch automatically finds your Claude Code OAuth session. No API keys to paste, no config files to edit, no accounts to create.

**[Download Pinch.exe](../../releases/latest)**

---

## Why Pinch?

| Problem | How Pinch Helps |
|---------|-----------------|
| "I got rate limited mid-conversation" | See your usage climbing in real-time and pace yourself |
| "I don't know when my limit resets" | Live countdown timer right on your taskbar |
| "I forgot to check my weekly usage" | Always visible — green/yellow/red at a glance |
| "I burned through my extra credits" | Extra usage tracking with dollar amounts shown |

---

## What's Under the Hood

Pinch is intentionally simple and paranoid about your privacy:

- **Zero telemetry** — no analytics, no tracking, no phone-home. The only network call is to `api.anthropic.com`.
- **No credentials stored** — your OAuth token is read fresh from Claude Code's file each poll and immediately discarded.
- **No backend** — everything runs locally on your machine.
- **Tiny footprint** — sits in your system tray, uses minimal resources.

| Detail | Value |
|--------|-------|
| Language | Python 3.10+ |
| UI Framework | tkinter (stdlib) |
| Tray Icon | pystray + Pillow |
| Exe Size | ~30 MB |
| Dependencies | 3 (pystray, Pillow, certifi) |
| Network | Anthropic API only |
| Data Stored | Display preferences only |

---

## Build from Source

```bash
git clone https://github.com/DarkCandyLord/pinch.git
cd pinch
pip install -r requirements.txt

python -m pinch              # Run directly
python -m pinch --test-api   # Test your connection
build.bat                    # Package as Pinch.exe
```

Requires Python 3.10+, Windows 10/11, and Claude Code authenticated.

---

## FAQ

**Q: Does this work without Claude Code?**
Not yet. Pinch reads the OAuth session that Claude Code creates. If you don't have Claude Code, the setup wizard will let you know.

**Q: Does this send my data anywhere?**
No. Pinch talks to `api.anthropic.com` to read your usage stats — the same endpoint Claude Code itself uses. Nothing else.

**Q: Will this slow down my computer?**
No. It polls every 30 seconds (configurable) and uses about 15MB of RAM. You won't notice it.

**Q: Can I change how often it checks?**
Yes — right-click the tray icon, choose Settings, and pick 15s / 30s / 60s / 2 min.

---

## Why "Pinch"?

Because crabs pinch, claws grip, and you should know when you're about to get clamped by your rate limits. Also it's small — it pinches onto your taskbar and doesn't let go.

---

<p align="center">
  MIT License &bull; Made by <a href="https://github.com/DarkCandyLord">DarkCandyLord</a>
</p>
