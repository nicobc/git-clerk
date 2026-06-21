import re

from acta.git import git

TYPES = frozenset(
    [
        "build",
        "chore",
        "ci",
        "docs",
        "feat",
        "fix",
        "perf",
        "refactor",
        "revert",
        "style",
        "test",
    ]
)

# type/scope, with an optional third descriptive segment (e.g. an issue topic);
# the conventional-commit type and scope are derived from the first two.
_BRANCH_RE = re.compile(r"([^/]+)/([^/]+)(?:/.+)?")
_SCOPE_RE = re.compile(r"[a-z0-9][a-z0-9_-]*", re.IGNORECASE)


def parse(branch: str) -> tuple[str, str]:
    branch_match = _BRANCH_RE.fullmatch(branch)
    if not branch_match:
        raise ValueError(f"Branch '{branch}' does not follow type/scope convention")
    type_ = branch_match.group(1)
    if type_ not in TYPES:
        raise ValueError(
            f"'{type_}' is not a conventional commit type. Use one of: {', '.join(sorted(TYPES))}"
        )
    scope = branch_match.group(2)
    if not _SCOPE_RE.fullmatch(scope):
        raise ValueError(
            f"'{scope}' is not a valid scope. Use letters, digits, hyphens, and underscores."
        )
    return type_, scope


def get_current_branch() -> str:
    return git("branch", "--show-current", capture=True)


def fetch_origin() -> None:
    git("fetch", "origin", quiet=True)


def switch_new_branch(name: str) -> None:
    git("switch", "-c", name, "origin/main", quiet=True)


def switch_main() -> None:
    git("switch", "main", quiet=True)


def pull_origin_main() -> None:
    git("pull", "origin", "main", quiet=True)


def branch_exists(name: str) -> bool:
    return bool(git("branch", "--list", name, capture=True))


def delete_branch(name: str) -> None:
    git("branch", "-D", name, quiet=True)


def switch_branch(name: str) -> None:
    git("switch", name, quiet=True)


def merge_origin_main() -> None:
    git("merge", "origin/main", quiet=True)
