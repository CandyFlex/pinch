"""Entry point for Pinch.

SECURITY MODEL:
- The --test-api flag NEVER prints tokens, credentials, or partial keys.
- Only usage percentages and reset times are displayed.
"""

import ctypes
import logging
import sys


def _enable_dpi_awareness() -> None:
    """Tell Windows we handle DPI ourselves so coordinates aren't virtualized."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # Win8.1 fallback
        except (AttributeError, OSError):
            pass


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    datefmt = "%H:%M:%S"

    # Console handler
    logging.basicConfig(level=level, format=fmt, datefmt=datefmt)

    # File handler — always logs to pinch.log next to the script
    # so we can diagnose crashes after the fact
    from pathlib import Path
    log_path = Path(__file__).resolve().parent.parent.parent / "pinch.log"
    try:
        fh = logging.FileHandler(str(log_path), mode="w", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        logging.getLogger().addHandler(fh)
    except OSError:
        pass  # can't write log file — not fatal


def main() -> None:
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print("Pinch — Know your limits before they know you.")
        print()
        print("Usage:")
        print("  python -m pinch              Start Pinch")
        print("  python -m pinch --test-api   Test API connection")
        print("  python -m pinch --test-monitor Test live polling")
        print("  python -m pinch --verbose     Verbose logging")
        return

    verbose = "--verbose" in args or "-v" in args
    _setup_logging(verbose)

    # DPI awareness must be set before any window creation
    _enable_dpi_awareness()

    if "--test-api" in args:
        _test_api()
        return

    if "--test-monitor" in args:
        _test_monitor()
        return

    # Normal launch
    from .app import App
    app = App()
    app.run()


def _test_api() -> None:
    """One-shot API test: fetch and print current usage.

    SECURITY: Never prints tokens or credentials — only usage data.
    """
    from .auth import test_connection

    print("Testing OAuth connection...")
    success, msg = test_connection()

    if not success:
        print(f"ERROR: {msg}")
        sys.exit(1)

    # Fetch full data for display
    from .auth import read_access_token
    from .usage_api import fetch_usage

    token = read_access_token()
    if not token:
        print("ERROR: Could not read access token")
        sys.exit(1)

    data = fetch_usage(token)
    # Token goes out of scope here — not retained

    if data.error:
        print(f"ERROR: {data.error}")
        sys.exit(1)

    print(f"\n5-Hour Rolling:  {data.five_hour.utilization:.1f}%  (resets {data.five_hour.resets_at})")
    print(f"7-Day (Opus):    {data.seven_day.utilization:.1f}%  (resets {data.seven_day.resets_at})")
    print(f"7-Day (Sonnet):  {data.seven_day_sonnet.utilization:.1f}%  (resets {data.seven_day_sonnet.resets_at})")
    if data.extra_usage.is_enabled:
        print(f"Extra Usage:     ${data.extra_usage.used_credits:.2f} / ${data.extra_usage.monthly_limit:.2f} ({data.extra_usage.utilization:.1f}%)")
    else:
        print("Extra Usage:     Not enabled")
    print("\nAPI test PASSED")


def _test_monitor() -> None:
    """Run the monitor for a few cycles and print updates."""
    import time
    from .shared_state import SharedState
    from .usage_monitor import UsageMonitor

    state = SharedState()

    def on_update(data):
        if data.error:
            print(f"  ERROR: {data.error}")
        else:
            print(f"  5h:{data.five_hour.utilization:.0f}% | Wk:{data.seven_day.utilization:.0f}% | Sonnet:{data.seven_day_sonnet.utilization:.0f}%")

    state.on_change(on_update)

    monitor = UsageMonitor(state, interval=5)  # faster for testing
    print("Starting monitor (Ctrl+C to stop, polling every 5s)...")
    monitor.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        monitor.stop()
        print("Done.")


if __name__ == "__main__":
    main()
