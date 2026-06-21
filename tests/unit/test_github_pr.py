import pytest

from acta.github.pr import ChecksState, classify_rollup


def _check_run(status: str, conclusion: str | None = None) -> dict[str, object]:
    return {"__typename": "CheckRun", "status": status, "conclusion": conclusion}


def _status_context(state: str) -> dict[str, object]:
    return {"__typename": "StatusContext", "state": state}


@pytest.mark.parametrize(
    "nodes, expected",
    [
        ([], ChecksState.NONE),
        ([_check_run("COMPLETED", "SUCCESS")], ChecksState.PASSED),
        ([_check_run("COMPLETED", "SKIPPED")], ChecksState.PASSED),
        ([_check_run("COMPLETED", "NEUTRAL")], ChecksState.PASSED),
        ([_check_run("IN_PROGRESS")], ChecksState.PENDING),
        ([_check_run("QUEUED")], ChecksState.PENDING),
        ([_check_run("COMPLETED", "FAILURE")], ChecksState.FAILED),
        ([_check_run("COMPLETED", "TIMED_OUT")], ChecksState.FAILED),
        ([_check_run("COMPLETED", "CANCELLED")], ChecksState.FAILED),
        # mixed precedence: a failure outranks a pending check
        (
            [_check_run("IN_PROGRESS"), _check_run("COMPLETED", "FAILURE")],
            ChecksState.FAILED,
        ),
        # mixed: all terminal-passing but one still running -> pending
        (
            [_check_run("COMPLETED", "SUCCESS"), _check_run("QUEUED")],
            ChecksState.PENDING,
        ),
        # legacy StatusContext nodes
        ([_status_context("SUCCESS")], ChecksState.PASSED),
        ([_status_context("PENDING")], ChecksState.PENDING),
        ([_status_context("FAILURE")], ChecksState.FAILED),
        ([_status_context("ERROR")], ChecksState.FAILED),
        # fail-safe: an unrecognised terminal conclusion is not green
        ([_check_run("COMPLETED", "WAT")], ChecksState.FAILED),
    ],
    ids=[
        "empty_none",
        "success",
        "skipped",
        "neutral",
        "in_progress",
        "queued",
        "failure",
        "timed_out",
        "cancelled",
        "failure_outranks_pending",
        "pending_when_one_running",
        "status_context_success",
        "status_context_pending",
        "status_context_failure",
        "status_context_error",
        "unknown_conclusion_fails_safe",
    ],
)
def test_classify_rollup(nodes: list[dict[str, object]], expected: ChecksState) -> None:
    assert classify_rollup(nodes) == expected
