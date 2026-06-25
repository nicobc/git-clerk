"""Per-branch acta working state: the issue and PR associated with each branch.

Stored as JSON under the repo's git dir (``.git/acta/state.json``), so it stays
local to the clone and is never committed. Keying state by branch confines each
issue/PR association to the branch it was created for.
"""

import json
import os

from acta.git import git

BranchState = dict[str, int | None]


def _get_state_path() -> str:
    """Return the absolute path to this clone's state file under the git dir."""
    git_dir = git("rev-parse", "--absolute-git-dir", capture=True)
    return os.path.join(git_dir, "acta", "state.json")


def _read() -> dict[str, BranchState]:
    """Load the branch→state map, returning an empty map when absent or unreadable."""
    try:
        with open(_get_state_path(), encoding="utf-8") as state_file:
            state: dict[str, BranchState] = json.load(state_file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return state


def _write(state: dict[str, BranchState]) -> None:
    """Persist the branch→state map, creating the state directory if needed."""
    path = _get_state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as state_file:
        json.dump(state, state_file, indent=2, sort_keys=True)
        state_file.write("\n")


def _entry(state: dict[str, BranchState], branch: str) -> BranchState:
    """Return ``branch``'s entry, inserting an empty one when it is missing."""
    return state.setdefault(branch, {"issue": None, "pr": None})


def get_branch_issue(branch: str) -> int | None:
    """Return the issue number recorded for ``branch``, or None."""
    entry = _read().get(branch)
    return entry.get("issue") if entry else None


def get_branch_pr(branch: str) -> int | None:
    """Return the PR number recorded for ``branch``, or None."""
    entry = _read().get(branch)
    return entry.get("pr") if entry else None


def set_branch_issue(branch: str, number: int) -> None:
    """Associate ``branch`` with issue ``number``, so ``acta pr`` can stamp Closes."""
    state = _read()
    _entry(state, branch)["issue"] = number
    _write(state)


def set_branch_pr(branch: str, number: int) -> None:
    """Record the PR ``number`` opened for ``branch``."""
    state = _read()
    _entry(state, branch)["pr"] = number
    _write(state)


def clear_branch(branch: str) -> None:
    """Drop all state for ``branch`` once it ships; a no-op if nothing is recorded."""
    state = _read()
    if branch in state:
        del state[branch]
        _write(state)
