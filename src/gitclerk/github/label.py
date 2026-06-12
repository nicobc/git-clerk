from gitclerk.git.branch import TYPES
from gitclerk.github import gh, repo

TYPE_COLORS: dict[str, str] = {
    "build": "0075ca",
    "chore": "cfd3d7",
    "ci": "e4e669",
    "docs": "0052cc",
    "feat": "a2eeef",
    "fix": "d73a4a",
    "perf": "5319e7",
    "refactor": "e99695",
    "revert": "f9d0c4",
    "style": "fef2c0",
    "test": "bfd4f2",
}


def ensure_type_labels() -> None:
    for type_ in TYPES:
        color = TYPE_COLORS.get(type_, "ededed")
        gh("label", "create", f"type: {type_}", "--color", color, "--force", "--repo", repo())
