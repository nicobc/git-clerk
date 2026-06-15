import json
import subprocess
from dataclasses import dataclass

from gitclerk.github import gh, repo
from gitclerk.github.label import ensure_type_labels


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


def issue_create(
    title: str,
    type_label: str,
    body: str = "",
    milestone: int | None = None,
) -> int:
    args = [
        "issue",
        "create",
        "--title",
        title,
        "--body",
        body,
        "--repo",
        repo(),
        "--label",
        f"type: {type_label}",
    ]
    if milestone is not None:
        args += ["--milestone", str(milestone)]
    try:
        url = gh(*args, capture=True)
    except subprocess.CalledProcessError:
        ensure_type_labels()
        url = gh(*args, capture=True)
    return int(url.rstrip("/").split("/")[-1])


def issue_list(milestone: int | None = None) -> list[IssueInfo]:
    args = [
        "issue",
        "list",
        "--repo",
        repo(),
        "--json",
        "number,title,labels,milestone",
        "--state",
        "open",
    ]
    if milestone is not None:
        args += ["--milestone", str(milestone)]
    out = gh(*args, capture=True)
    issues: list[IssueInfo] = []
    for raw in json.loads(out):
        ms_raw = raw["milestone"]
        issues.append(
            IssueInfo(
                number=int(raw["number"]),
                title=str(raw["title"]),
                type=_extract_type(raw["labels"]) or "",
                milestone=MilestoneRef(number=int(ms_raw["number"]), title=str(ms_raw["title"]))
                if ms_raw
                else None,
            )
        )
    return issues


def issue_view(number: int) -> IssueInfo:
    out = gh(
        "issue",
        "view",
        str(number),
        "--repo",
        repo(),
        "--json",
        "number,title,labels,milestone",
        capture=True,
    )
    raw = json.loads(out)
    ms_raw = raw["milestone"]
    type_ = _extract_type(raw["labels"])
    if not type_:
        raise RuntimeError(
            f"Issue #{number} has no type label — assign a 'type: TYPE' label on GitHub"
        )
    return IssueInfo(
        number=int(raw["number"]),
        title=str(raw["title"]),
        type=type_,
        milestone=MilestoneRef(number=int(ms_raw["number"]), title=str(ms_raw["title"]))
        if ms_raw
        else None,
    )


def issue_close_not_planned(number: int) -> None:
    gh("issue", "close", str(number), "--reason", "not planned", "--repo", repo())


def _extract_type(labels: list[dict[str, str]]) -> str | None:
    for label in labels:
        name = label.get("name", "")
        if name.startswith("type: "):
            return name[6:]
    return None
