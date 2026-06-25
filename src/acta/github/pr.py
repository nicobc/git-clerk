"""Open, inspect, and merge pull requests, and reduce their CI check state."""

import json
import re
import subprocess
from dataclasses import dataclass
from enum import Enum

from acta.git.branch import get_current_branch
from acta.github import get_repo, gh

_PASSING_CONCLUSIONS = {"SUCCESS", "NEUTRAL", "SKIPPED"}
_PASSING_STATUS_STATES = {"SUCCESS"}
_PENDING_STATUS_STATES = {"PENDING", "EXPECTED"}

# A check's "Details" URL ends with .../job/<id> for GitHub Actions check runs.
_JOB_URL_RE = re.compile(r"/job/(\d+)")


class ChecksState(Enum):
    """Aggregate CI state of a PR: no checks, still running, all green, or failed."""

    NONE = "none"
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True)
class CheckRun:
    """One CI check on a PR: its display name, reduced state, and "Details" URL."""

    name: str
    state: ChecksState
    details_url: str


def classify_node(node: dict[str, object]) -> ChecksState:
    """Reduce a single `statusCheckRollup` node to PENDING, PASSED, or FAILED.

    Handles both a `CheckRun` (GitHub Actions) and a legacy `StatusContext`. A
    check is pending until it reaches a terminal state, passing only on an
    explicitly successful one; any other terminal state counts as FAILED, so an
    unexpected state never reads as green.
    """
    if node.get("__typename") == "StatusContext":
        state = node.get("state")
        if state in _PENDING_STATUS_STATES:
            return ChecksState.PENDING
        return ChecksState.PASSED if state in _PASSING_STATUS_STATES else ChecksState.FAILED
    if node.get("status") != "COMPLETED":
        return ChecksState.PENDING
    if node.get("conclusion") in _PASSING_CONCLUSIONS:
        return ChecksState.PASSED
    return ChecksState.FAILED


def classify_rollup(nodes: list[dict[str, object]]) -> ChecksState:
    """Reduce a `statusCheckRollup` to one overall state.

    Fail-safe aggregation: FAILED if any check failed, else PENDING if any is
    still running, else PASSED. An empty list (no checks) is NONE.
    """
    if not nodes:
        return ChecksState.NONE
    states = [classify_node(node) for node in nodes]
    if ChecksState.FAILED in states:
        return ChecksState.FAILED
    if ChecksState.PENDING in states:
        return ChecksState.PENDING
    return ChecksState.PASSED


def fetch_rollup(pr_number: int) -> list[dict[str, object]]:
    """Fetch the PR's raw ``statusCheckRollup`` nodes for its latest commit.

    GitHub reports every CI check on the PR's head commit — each GitHub Actions
    job plus any older-style status checks — as a list it calls the
    "statusCheckRollup".
    """
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
    return parsed.get("statusCheckRollup") or []


def fetch_checks_state(pr_number: int) -> ChecksState:
    """Ask GitHub for the PR's CI results and reduce them to one overall state."""
    return classify_rollup(fetch_rollup(pr_number))


def fetch_checks(pr_number: int) -> list[CheckRun]:
    """Return each of the PR's CI checks with its name, reduced state, and Details URL.

    A CheckRun (GitHub Actions) carries ``name``/``detailsUrl``; a legacy
    StatusContext carries ``context``/``targetUrl`` instead — fall back across both.
    """
    checks: list[CheckRun] = []
    for node in fetch_rollup(pr_number):
        name = str(node.get("name") or node.get("context") or "check")
        details_url = str(node.get("detailsUrl") or node.get("targetUrl") or "")
        checks.append(CheckRun(name, classify_node(node), details_url))
    return checks


def fetch_failed_log(check: CheckRun, line_count: int) -> str:
    """Return the tail of a failed check's failed-step log, or '' if unavailable.

    Resolves the Actions job id from the check's Details URL and asks gh for just
    the failed steps (``gh run view --log-failed``), keeping the last
    ``line_count`` lines. Best-effort: returns '' when there is no job id (e.g. a
    legacy status context) or gh cannot produce a log.
    """
    match = _JOB_URL_RE.search(check.details_url)
    if match is None:
        return ""
    try:
        log = gh(
            "run",
            "view",
            "--job",
            match.group(1),
            "--log-failed",
            "--repo",
            get_repo(),
            capture=True,
        )
    except subprocess.CalledProcessError:
        return ""
    return "\n".join(log.splitlines()[-line_count:])


def pr_create(title: str, body: str, base: str = "main") -> tuple[int, str]:
    """Open a PR for the current branch against ``base``; return its ``(number, url)``."""
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
    """Return the ``(number, title)`` of the PR for the current branch."""
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


def pr_closing_issues(pr_number: int) -> list[int]:
    """Return the issue numbers the PR closes on merge, from its ``Closes #N`` links."""
    response_json = gh(
        "pr",
        "view",
        str(pr_number),
        "--repo",
        get_repo(),
        "--json",
        "closingIssuesReferences",
        capture=True,
    )
    data: dict[str, list[dict[str, int]]] = json.loads(response_json)
    references = data.get("closingIssuesReferences") or []
    return [int(reference["number"]) for reference in references]


def pr_checks_pass(pr_number: int) -> bool:
    """Return True if the PR's checks are green or there are none (nothing gating)."""
    return fetch_checks_state(pr_number) in {ChecksState.PASSED, ChecksState.NONE}


def pr_merge(pr_number: int) -> None:
    """Squash-merge the PR and delete its remote branch."""
    gh("pr", "merge", str(pr_number), "--squash", "--delete-branch", "--repo", get_repo())
