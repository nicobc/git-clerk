"""Watch a PR's CI checks: report each as it finishes and surface failures.

Used by ``acta pr`` (after opening) and ``acta watch``. Unlike
``gh pr checks --watch``, which reprints the whole table on every tick, this
echoes one line per check as it reaches a terminal state, prints the failing
job's log on failure, and raises so the command exits non-zero.
"""

import sys
import time

import click

from acta.github.pr import (
    CheckRun,
    ChecksState,
    fetch_checks,
    fetch_checks_state,
    fetch_failed_log,
)

_POLL_INTERVAL = 5  # seconds between check polls
_QUEUE_TIMEOUT = 20  # seconds to wait for checks to register before giving up
_FAILURE_LOG_LINES = 40  # tail length when surfacing a failed check's log


def _echo_and_flush(message: str) -> None:
    """Echo a line and flush, so progress streams live even when stdout is piped."""
    click.echo(message)
    sys.stdout.flush()


def format_check(check: CheckRun) -> str:
    """Render a finished check as a one-line transition: ✓ on pass, ✗ on fail."""
    mark = "✓" if check.state is ChecksState.PASSED else "✗"
    return f"{mark} {check.name}"


def await_checks(pr_number: int) -> bool:
    """Poll until at least one check registers; return False if none appears in time."""
    for _ in range(_QUEUE_TIMEOUT // _POLL_INTERVAL):
        if fetch_checks_state(pr_number) is not ChecksState.NONE:
            return True
        time.sleep(_POLL_INTERVAL)
    return False


def watch_checks(pr_number: int) -> None:
    """Report each check as it finishes, surfacing failures and raising on any failure.

    Echoes one line per check only as it reaches a terminal state. On failure it
    prints the failing job's log tail and raises ``ClickException`` so the
    command exits non-zero. Returns quietly if no checks ever appear.
    """
    if not await_checks(pr_number):
        return
    _echo_and_flush("Now watching checks...")
    reported: set[str] = set()
    while True:
        checks = fetch_checks(pr_number)
        for check in checks:
            if check.state is ChecksState.PENDING or check.name in reported:
                continue
            reported.add(check.name)
            _echo_and_flush(format_check(check))
        failures = [check for check in checks if check.state is ChecksState.FAILED]
        if failures:
            for check in failures:
                log = fetch_failed_log(check, _FAILURE_LOG_LINES)
                if log:
                    _echo_and_flush(log)
            raise click.ClickException(f"PR #{pr_number} checks failed.")
        if checks and all(check.state is not ChecksState.PENDING for check in checks):
            _echo_and_flush("All checks passed.")
            return
        time.sleep(_POLL_INTERVAL)
