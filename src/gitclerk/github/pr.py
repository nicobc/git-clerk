import json
import time
from enum import Enum

from gitclerk.git.branch import get_current_branch
from gitclerk.github import get_repo, gh

_CHECKS_POLL_INTERVAL = 5  # seconds
_CHECKS_QUEUE_TIMEOUT = 90  # seconds to wait for checks to appear

_PASSING_CONCLUSIONS = {"SUCCESS", "NEUTRAL", "SKIPPED"}
_PASSING_STATUS_STATES = {"SUCCESS"}
_PENDING_STATUS_STATES = {"PENDING", "EXPECTED"}


class ChecksState(Enum):
    NONE = "none"
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


def classify_rollup(nodes: list[dict[str, object]]) -> ChecksState:
    """Reduce a `statusCheckRollup` to one state.

    Each node is a `CheckRun` (GitHub Actions) or a legacy `StatusContext`. A check is
    pending until it reaches a terminal state, passing only on an explicitly successful
    one. Fail-safe: any terminal check that is not recognised as passing counts as
    FAILED, so an unexpected state never reads as green on a ship gate.
    """
    if not nodes:
        return ChecksState.NONE
    any_pending = False
    for node in nodes:
        if node.get("__typename") == "StatusContext":
            state = node.get("state")
            if state in _PENDING_STATUS_STATES:
                any_pending = True
            elif state not in _PASSING_STATUS_STATES:
                return ChecksState.FAILED
        elif node.get("status") != "COMPLETED":
            any_pending = True
        elif node.get("conclusion") not in _PASSING_CONCLUSIONS:
            return ChecksState.FAILED
    return ChecksState.PENDING if any_pending else ChecksState.PASSED


def fetch_checks_state(pr_number: int) -> ChecksState:
    response_json = gh(
        "pr",
        "view",
        str(pr_number),
        "--repo",
        get_repo(),
        "--json",
        "statusCheckRollup",
        capture=True,
    )
    parsed: dict[str, list[dict[str, object]]] = json.loads(response_json)
    return classify_rollup(parsed.get("statusCheckRollup") or [])


def pr_create(title: str, body: str, base: str = "main") -> tuple[int, str]:
    command_args = [
        "pr",
        "create",
        "--base",
        base,
        "--title",
        title,
        "--body",
        body,
        "--repo",
        get_repo(),
    ]
    pr_url = gh(*command_args, capture=True)
    pr_number = int(pr_url.rstrip("/").split("/")[-1])
    return pr_number, pr_url


def pr_view() -> tuple[int, str]:
    response_json = gh(
        "pr",
        "view",
        get_current_branch(),
        "--repo",
        get_repo(),
        "--json",
        "number,title",
        capture=True,
    )
    pr_data = json.loads(response_json)
    return int(pr_data["number"]), str(pr_data["title"])


def pr_checks_pass(pr_number: int) -> bool:
    return fetch_checks_state(pr_number) in {ChecksState.PASSED, ChecksState.NONE}


def pr_merge(pr_number: int) -> None:
    gh("pr", "merge", str(pr_number), "--squash", "--delete-branch", "--repo", get_repo())


def pr_checks_watch(pr_number: int) -> None:
    for _ in range(_CHECKS_QUEUE_TIMEOUT // _CHECKS_POLL_INTERVAL):
        if fetch_checks_state(pr_number) is not ChecksState.NONE:
            break
        time.sleep(_CHECKS_POLL_INTERVAL)
    else:
        return  # no checks ever appeared — nothing to watch
    gh("pr", "checks", str(pr_number), "--repo", get_repo(), "--watch")
