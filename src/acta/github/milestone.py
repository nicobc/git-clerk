import json
from dataclasses import dataclass

from acta.github import get_repo, gh

_SCOPE_PREFIX = "scope: "


@dataclass
class MilestoneListItem:
    number: int
    title: str
    scope: str
    description: str
    open_issues: int
    closed_issues: int


@dataclass
class MilestoneDetail:
    number: int
    title: str
    scope: str
    description: str
    open_issues: int
    state: str


def milestone_create(
    title: str,
    scope: str,
    description: str = "",
) -> int:
    gh_description = _build_description(scope, description)
    response_json = gh(
        "api",
        f"repos/{get_repo()}/milestones",
        "--method",
        "POST",
        "-f",
        f"title={title}",
        "-f",
        f"description={gh_description}",
        capture=True,
    )
    return int(json.loads(response_json)["number"])


def milestone_list() -> list[MilestoneListItem]:
    response_json = gh(
        "api", f"repos/{get_repo()}/milestones", "-X", "GET", "-f", "state=open", capture=True
    )
    milestone_items: list[MilestoneListItem] = []
    for milestone_data in json.loads(response_json):
        scope, description = parse_description(str(milestone_data.get("description") or ""))
        milestone_items.append(
            MilestoneListItem(
                number=int(milestone_data["number"]),
                title=str(milestone_data["title"]),
                scope=scope,
                description=description,
                open_issues=int(milestone_data["open_issues"]),
                closed_issues=int(milestone_data["closed_issues"]),
            )
        )
    return milestone_items


def milestone_view(number: int) -> MilestoneDetail:
    response_json = gh("api", f"repos/{get_repo()}/milestones/{number}", capture=True)
    milestone_data = json.loads(response_json)
    scope, description = parse_description(str(milestone_data.get("description") or ""))
    return MilestoneDetail(
        number=int(milestone_data["number"]),
        title=str(milestone_data["title"]),
        scope=scope,
        description=description,
        open_issues=int(milestone_data["open_issues"]),
        state=str(milestone_data["state"]),
    )


def milestone_reopen(number: int) -> None:
    gh("api", f"repos/{get_repo()}/milestones/{number}", "--method", "PATCH", "-f", "state=open")


def milestone_close(number: int) -> None:
    gh("api", f"repos/{get_repo()}/milestones/{number}", "--method", "PATCH", "-f", "state=closed")


def _build_description(scope: str, description: str) -> str:
    description_parts = [f"scope: {scope}"]
    if description:
        description_parts.append(description)
    return "\n\n".join(description_parts)


def parse_description(raw_description: str) -> tuple[str, str]:
    """Returns (scope, description) from a GitHub milestone description."""
    lines = raw_description.split("\n")
    scope = ""
    if lines and lines[0].startswith(_SCOPE_PREFIX):
        scope = lines[0][len(_SCOPE_PREFIX) :]
        remaining_description = "\n".join(lines[1:]).strip()
    else:
        remaining_description = raw_description.strip()
    return scope, remaining_description
