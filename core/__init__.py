"""core — V18 business logic package.

Importing this package automatically installs the local-first crash handler
(`core.error_reporter.install_crash_handler()`). All unhandled exceptions in
any process that imports `core` will be logged to `outputs/crash_logs/v18.log`
(JSON, daily rotation, 14-day retention). Nothing is sent over the network.
"""

from __future__ import annotations

# Install the crash handler as early as possible so even import-time errors
# are captured. Idempotent — safe to import core multiple times.
try:
    from core.error_reporter import install_crash_handler

    install_crash_handler()
except Exception:  # noqa: BLE001
    # If crash handler setup itself fails, don't break imports.
    # (The error will be visible via Python's default stderr handler.)
    pass
