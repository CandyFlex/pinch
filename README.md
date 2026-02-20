<p align="center">
  <img src="docs/screenshots/banner.png" alt="Wick" width="100%" />
</p>

<p align="center">
  <a href="../../actions/workflows/release.yml"><img src="https://img.shields.io/github/actions/workflow/status/CandyFlex/wick/release.yml?style=flat-square&label=build" /></a>
  <a href="../../releases/latest"><img src="https://img.shields.io/github/v/release/CandyFlex/wick?style=flat-square" /></a>
  <img src="https://img.shields.io/github/downloads/CandyFlex/wick/total?style=flat-square&label=downloads" />
  <img src="https://img.shields.io/badge/platform-Windows-0078D4?style=flat-square&logo=windows&logoColor=white" />
  <img src="https://img.shields.io/github/license/CandyFlex/wick?style=flat-square" />
  <img src="https://img.shields.io/badge/telemetry-zero-brightgreen?style=flat-square" />
</p>

<p align="center">
  <img src="docs/screenshots/hero.png" alt="Wick on the Windows taskbar" width="560" />
</p>

---

A small taskbar pill that shows your Claude subscription utilization, a live countdown to your next reset, and your weekly quota — color-coded so you know at a glance whether to keep going or ease up.

- **Taskbar pill** — current utilization %, reset countdown, weekly usage. Green/yellow/red at a glance.
- **Detail popup** — click the pill for 5-hour rolling, 7-day Opus, 7-day Sonnet, and extra usage ($) with progress bars and reset timers.
- **Settings** — right-click the tray icon to adjust polling speed (15s–2min), auto-start with Windows, or test your connection.

---

## Install

**Run from source** (recommended):
```bash
git clone https://github.com/CandyFlex/wick.git
cd wick
pip install -r requirements.txt
python -m wick
```

**Or install via pip:**
```bash
pip install wick-monitor
wick
```

<details>
<summary><strong>Or download the exe</strong></summary>

Grab `Wick.exe` from [Releases](../../releases/latest). Requires Windows 10/11 and [Claude Code](https://docs.anthropic.com/en/docs/claude-code) authenticated.

This binary is built by [GitHub Actions](.github/workflows/release.yml) from the public source code — not on anyone's personal machine. Every release includes a SHA256 checksum for verification.

> **Note:** Windows SmartScreen may warn about an unrecognized app. This is normal for new open-source tools. Click "More info" → "Run anyway", or [build from source](#install) instead.

</details>

Wick reads your existing Claude Code OAuth session automatically. No API keys to paste, no config files, no accounts to create.

---

## Why This Exists

macOS already has [half a dozen native Claude usage trackers](https://github.com/topics/claude-usage). Windows had almost nothing — one Electron-based widget at 150MB+.

Wick is the lightweight alternative: ~2,500 lines of Python, 30MB exe (no Electron), zero dependencies beyond the standard library and three small packages.

---

## Security & Trust

Wick touches your OAuth token, so you should understand exactly what it does:

- **The only network call** is to `api.anthropic.com/v1/organizations/{org}/usage` — the same endpoint Claude Code uses. Nothing else. No analytics, no tracking, no phone-home.
- **Your token is read live** from `~/.claude/.credentials.json` each poll cycle and immediately discarded. It is never written to disk, cached, or sent anywhere except Anthropic's API.
- **No backend.** There is no Wick server. Everything runs on your machine.
- **Fully auditable.** The entire codebase is ~2,500 lines of Python across 17 files. The auth logic is in [`auth.py`](src/wick/auth.py) (67 lines). The API call is in [`usage_api.py`](src/wick/usage_api.py) (97 lines). Read them yourself.

| | |
|---|---|
| Source | ~2,500 lines of Python |
| Exe size | ~30 MB |
| RAM usage | ~15 MB |
| Dependencies | 3 ([pystray](https://pypi.org/project/pystray/), [Pillow](https://pypi.org/project/pillow/), [certifi](https://pypi.org/project/certifi/)) |
| Network | `api.anthropic.com` only |
| Data stored | Display preferences in `%LOCALAPPDATA%/Wick/` |

---

<details>
<summary><strong>Troubleshooting</strong></summary>

**The pill turned red / shows an error**
Your OAuth token probably expired. Claude Code tokens last ~24 hours. Wick will automatically retry a few times, but if it can't recover:
1. Open Claude Code (or run any `claude` command in your terminal) — this refreshes the token
2. Right-click the Wick tray icon → **Reconnect**

That's it. Wick re-reads the credentials file and picks up the fresh token immediately.

**"No OAuth token — is Claude Code installed?"**
Wick reads `~/.claude/.credentials.json`, which Claude Code creates when you authenticate. If this file doesn't exist, [install Claude Code](https://docs.anthropic.com/en/docs/claude-code) and sign in first.

**The pill disappeared from my taskbar**
It may have been moved to the system tray overflow (the `^` arrow). Look for the Wick icon there. You can drag it back to the taskbar.

</details>

<details>
<summary><strong>Common Questions</strong></summary>

**Does this work without Claude Code?**
Not yet. Wick reads the OAuth session that Claude Code creates. If Claude Code isn't installed, the setup wizard tells you what to do.

**Will this slow down my computer?**
No. ~15 MB of RAM, one API call every 30 seconds (configurable). You won't notice it.

**Can I change the polling interval?**
Yes. Right-click the tray icon → Settings → pick 15s, 30s, 60s, or 2 minutes.

**Why is the exe 30MB?**
PyInstaller bundles the entire Python runtime. The actual source code is ~50KB. If you have Python installed, `pip install wick-monitor` avoids the bundled runtime entirely.

**Why is it called Wick?**
A wick burns down — just like your token budget. When the wick is short, you're almost out. It sits on your taskbar and tells you how much flame you've got left.

</details>

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome — especially for Linux/macOS support.

---

<p align="center">
  <sub>MIT License · Built by <a href="https://github.com/CandyFlex">CandyFlex</a></sub>
</p>
