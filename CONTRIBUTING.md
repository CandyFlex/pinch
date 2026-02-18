# Contributing to Pinch

Pinch is open source under the MIT License. Contributions are welcome.

## Quick Start

```bash
git clone https://github.com/CandyFlex/pinch.git
cd pinch
pip install -r requirements.txt
python -m pinch
```

## Project Structure

All source code lives in `src/pinch/`:

| File | Purpose |
|------|---------|
| `app.py` | Main app coordinator |
| `auth.py` | OAuth token reader (reads from Claude Code's session file) |
| `usage_api.py` | Anthropic API calls |
| `usage_monitor.py` | Poll loop and state updates |
| `shared_state.py` | Thread-safe shared data |
| `taskbar_overlay.py` | The taskbar pill widget |
| `popup_view.py` | Detail popup overlay |
| `tray_icon.py` | System tray icon and menu |
| `settings.py` | Persistent config (JSON in %LOCALAPPDATA%) |
| `settings_ui.py` | Settings window |
| `setup_wizard.py` | First-run auth setup |
| `config.py` | Constants and branding |
| `autostart.py` | Windows registry startup |
| `theme.py` | Color theme definitions |
| `utils.py` | Utility helpers |

## Guidelines

- Keep it simple. Pinch is intentionally small.
- No telemetry, analytics, or network calls except to `api.anthropic.com`.
- No credential storage. OAuth tokens are read live and discarded.
- Test with `python -m pinch --test-api` before submitting.

## Submitting Changes

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/your-change`)
3. Make your changes
4. Test locally with `python -m pinch`
5. Submit a pull request

## Reporting Issues

Open an issue on GitHub with:
- What you expected to happen
- What actually happened
- Your Windows version and Python version
