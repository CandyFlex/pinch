"""Entry point for Pinch.

SECURITY MODEL:
- The --test-api flag NEVER prints tokens, credentials, or partial keys.
- Only usage percentages and reset times are displayed.
"""

import logging
import sys


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


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
