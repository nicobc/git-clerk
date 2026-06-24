"""Create, list, and view GitHub milestones.

GitHub milestones have no native "scope" field, so acta encodes the branch scope
as a leading ``scope: <scope>`` line in the milestone's description and parses it
back out on read.
"""

import json
from dataclasses import dataclass

from acta.github import get_repo, gh

_SCOPE_PREFIX = "scope: "


@dataclass
class MilestoneListItem:
    """A milestone in a list view, with open/closed issue counts."""

    number: int
    title: str
    scope: str
    description: str
    open_issues: int
    closed_issues: int


@dataclass
class MilestoneDetail:
    """A single milestone's detail, including its open/closed state."""

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
    """Create a milestone, encoding ``scope`` into its description; return its number."""
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
    """Return all open milestones, with scope parsed out of each description."""
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
    """Fetch one milestone's detail, with scope parsed out of its description."""
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
    """Reopen a closed milestone.

    Captures the PATCH response so gh's raw milestone JSON is swallowed instead
    of printed — the gh wrapper echoes stdout to the terminal when not captured.
    """
    gh(
        "api",
        f"repos/{get_repo()}/milestones/{number}",
        "--method",
        "PATCH",
        "-f",
        "state=open",
        capture=True,
    )


def milestone_close(number: int) -> None:
    """Close a milestone (done automatically when its last issue ships).

    Captures the PATCH response so gh's raw milestone JSON is swallowed instead
    of printed — the gh wrapper echoes stdout to the terminal when not captured.
    """
    gh(
        "api",
        f"repos/{get_repo()}/milestones/{number}",
        "--method",
        "PATCH",
        "-f",
        "state=closed",
        capture=True,
    )


def _build_description(scope: str, description: str) -> str:
    """Encode ``scope`` as a leading ``scope: …`` line above the free-text description."""
    description_parts = [f"scope: {scope}"]
    if description:
        description_parts.append(description)
    return "\n\n".join(description_parts)


def parse_description(raw_description: str) -> tuple[str, str]:
    """Split a milestone description into its ``(scope, description)`` parts.

    Inverse of ``_build_description``: reads the scope from a leading ``scope: …``
    line if present, returning an empty scope otherwise.

    Example:
        >>> parse_description("scope: auth\\n\\nHandles login.")
        ('auth', 'Handles login.')
    """
    lines = raw_description.split("\n")
    scope = ""
    if lines and lines[0].startswith(_SCOPE_PREFIX):
        scope = lines[0][len(_SCOPE_PREFIX) :]
        remaining_description = "\n".join(lines[1:]).strip()
    else:
        remaining_description = raw_description.strip()
    return scope, remaining_description
