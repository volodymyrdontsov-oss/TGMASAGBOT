"""Optional systemd watchdog integration.

When the bot is run under a systemd unit with `Type=notify` and
`WatchdogSec=N`, the supervisor will kill + restart the process if it
doesn't receive a `WATCHDOG=1` notification within N seconds. This is the
last line of defence against the monitor loop wedging on a stalled
network call (see `ITERATION_TIMEOUT` in `src.config` for the first one).

Outside systemd — e.g. running locally for development — the `sdnotify`
package may not be installed and the `NOTIFY_SOCKET` env var won't be
set; in either case all calls here become silent no-ops.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

try:
    import sdnotify  # type: ignore[import-not-found]

    _notifier = sdnotify.SystemdNotifier()
except ImportError:
    _notifier = None


def ready() -> None:
    """Tell systemd we've finished startup. Required for `Type=notify`."""
    if _notifier is None:
        return
    _notifier.notify("READY=1")
    log.debug("sd_notify READY=1")


def alive() -> None:
    """Pet the watchdog. Call once per successful monitor iteration."""
    if _notifier is None:
        return
    _notifier.notify("WATCHDOG=1")
