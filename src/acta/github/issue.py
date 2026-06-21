import json
import subprocess
from dataclasses import dataclass

from acta.github import get_repo, gh
from acta.github.label import ensure_type_labels
from acta.github.milestone import milestone_view


@dataclass
class MilestoneRef:
    number: int
    title: str


@dataclass
class IssueInfo:
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
    gh("issue", "close", str(number), "--reason", "not planned", "--repo", get_repo())


def _extract_type(labels: list[dict[str, str]]) -> str | None:
    for label in labels:
        name = label.get("name", "")
        if name.startswith("type: "):
            return name[6:]
    return None
