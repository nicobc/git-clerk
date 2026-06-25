"""Create, list, and view GitHub issues, including their type label and milestone."""

import json
import subprocess
from dataclasses import dataclass

from acta.github import get_repo, gh
from acta.github.label import ensure_type_labels
from acta.github.milestone import milestone_view


@dataclass
class MilestoneRef:
    """The milestone an issue belongs to (number and title only)."""

    number: int
    title: str


@dataclass
class IssueInfo:
    """A GitHub issue: number, title, conventional-commit type, milestone, and body."""

    number: int
    title: str
    type: str
    milestone: MilestoneRef | None
    body: str = ""


def issue_create(
    title: str,
    type_label: str,
    body: str = "",
    milestone: int | None = None,
) -> int:
    """Create an issue with a ``type: <type_label>`` label and optional milestone.

    If the type label doesn't exist yet, the first create fails; the label set is
    then provisioned via ``ensure_type_labels`` and the create is retried once.

    Args:
        title: Issue title.
        type_label: Conventional-commit type, becomes the ``type: …`` label.
        body: Issue body markdown.
        milestone: Milestone number to attach, or None.

    Returns:
        The new issue's number.
    """
    milestone_title = milestone_view(milestone).title if milestone is not None else None
    command_args = [
        "issue",
        "create",
        "--title",
        title,
        "--body",
        body,
        "--repo",
        get_repo(),
        "--label",
        f"type: {type_label}",
    ]
    if milestone_title is not None:
        command_args += ["--milestone", milestone_title]
    try:
        issue_url = gh(*command_args, capture=True)
    except subprocess.CalledProcessError:
        ensure_type_labels()
        issue_url = gh(*command_args, capture=True)
    return int(issue_url.rstrip("/").split("/")[-1])


def issue_list(milestone: int | None = None) -> list[IssueInfo]:
    """Return the open issues, optionally filtered to one milestone."""
    command_args = [
        "issue",
        "list",
        "--repo",
        get_repo(),
        "--json",
        "number,title,labels,milestone",
        "--state",
        "open",
    ]
    if milestone is not None:
        command_args += ["--milestone", str(milestone)]
    response_json = gh(*command_args, capture=True)
    issues: list[IssueInfo] = []
    for issue_data in json.loads(response_json):
        milestone_data = issue_data["milestone"]
        issues.append(
            IssueInfo(
                number=int(issue_data["number"]),
                title=str(issue_data["title"]),
                type=_extract_type(issue_data["labels"]) or "",
                milestone=MilestoneRef(
                    number=int(milestone_data["number"]), title=str(milestone_data["title"])
                )
                if milestone_data
                else None,
            )
        )
    return issues


def issue_view(number: int) -> IssueInfo:
    """Fetch a single issue, including its body.

    Raises:
        RuntimeError: If the issue has no ``type: …`` label, since the workflow
            derives the branch/commit type from it.
    """
    response_json = gh(
        "issue",
        "view",
        str(number),
        "--repo",
        get_repo(),
        "--json",
        "number,title,labels,milestone,body",
        capture=True,
    )
    issue_data = json.loads(response_json)
    milestone_data = issue_data["milestone"]
    issue_type = _extract_type(issue_data["labels"])
    if not issue_type:
        raise RuntimeError(
            f"Issue #{number} has no type label — assign a 'type: TYPE' label on GitHub"
        )
    return IssueInfo(
        number=int(issue_data["number"]),
        title=str(issue_data["title"]),
        type=issue_type,
        milestone=MilestoneRef(
            number=int(milestone_data["number"]), title=str(milestone_data["title"])
        )
        if milestone_data
        else None,
        body=str(issue_data.get("body") or ""),
    )


def issue_close_not_planned(number: int) -> None:
    """Close an issue as "not planned" (discarded rather than completed)."""
    gh("issue", "close", str(number), "--reason", "not planned", "--repo", get_repo())


def issue_reopen(number: int) -> None:
    """Reopen a previously closed issue."""
    gh("issue", "reopen", str(number), "--repo", get_repo())


def issue_edit(
    number: int,
    title: str | None = None,
    body: str | None = None,
    milestone: int | None = None,
    type_label: str | None = None,
) -> None:
    """Edit an issue's title, body, milestone, and/or type label; unset fields stay.

    The milestone is passed to gh by title, as ``gh issue edit`` expects the
    name. Changing the type swaps the ``type: …`` label; if the new label does
    not exist yet, the edit is retried once after provisioning the label set
    (mirroring ``issue_create``). Captures gh's issue-URL output.
    """
    command_args = ["issue", "edit", str(number), "--repo", get_repo()]
    if title is not None:
        command_args += ["--title", title]
    if body is not None:
        command_args += ["--body", body]
    if milestone is not None:
        command_args += ["--milestone", milestone_view(milestone).title]
    if type_label is None:
        gh(*command_args, capture=True)
        return
    current_type = issue_view(number).type
    command_args += [
        "--remove-label",
        f"type: {current_type}",
        "--add-label",
        f"type: {type_label}",
    ]
    try:
        gh(*command_args, capture=True)
    except subprocess.CalledProcessError:
        ensure_type_labels()
        gh(*command_args, capture=True)


def _extract_type(labels: list[dict[str, str]]) -> str | None:
    """Return the type from the first ``type: …`` label, or None if absent."""
    for label in labels:
        name = label.get("name", "")
        if name.startswith("type: "):
            return name[6:]
    return None
