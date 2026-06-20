#!/usr/bin/env python3
"""Cut a git-clerk release: bump the version, ship it, tag it, and watch the publish job.

Maintainer-only — this script is not part of the published package. Run from the repo root:

    uv run scripts/release.py {patch|minor|major}

Git tags are the source of truth for the version; pyproject.toml is overwritten to mirror
the new tag. The version is computed from the existing tags with the same function `git
clerk release` uses, so the script and the tag it pushes always agree.
"""

import argparse
import re
import subprocess
import time
from pathlib import Path

from gitclerk.git.tag import compute_next_semver, fetch_tags, latest_semver_tag, list_tags

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
PUBLISH_WORKFLOW = "publish.yml"
RUN_POLL_INTERVAL = 5  # seconds between checks for the publish run to appear
RUN_QUEUE_TIMEOUT = 60  # give up if the publish run has not appeared within this many seconds

_VERSION_RE = re.compile(r'^version = ".*"', re.MULTILINE)
_HEADER_RE = re.compile(r"(?P<type>\w+)(\([^)]*\))?!?:")  # conventional commit header
_BUMP_RANK = {"patch": 0, "minor": 1, "major": 2}


def run(*command: str) -> None:
    subprocess.run(command, check=True)


def capture(*command: str) -> str:
    return subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE).stdout.strip()


def write_pyproject_version(new_version: str) -> None:
    new_text, replaced = _VERSION_RE.subn(
        f'version = "{new_version}"', PYPROJECT.read_text(), count=1
    )
    if not replaced:
        raise SystemExit("release: no version line found in pyproject.toml")
    PYPROJECT.write_text(new_text)


def required_bump_since(tag: str) -> str:
    """The minimum bump justified by the commits since `tag`.

    `feat` since the last release implies `minor`; everything else, `patch`. `major` is
    never inferred — there is no breaking-change marker in the squash history, and pre-1.0
    a breaking change does not imply a major bump anyway.
    """
    subjects = capture("git", "log", f"{tag}..origin/main", "--format=%s").splitlines()
    for subject in subjects:
        header = _HEADER_RE.match(subject)
        if header is not None and header.group("type") == "feat":
            return "minor"
    return "patch"


def wait_for_publish_run(tag: str) -> str:
    """Poll until the publish run triggered by `tag` appears, then return its id."""
    deadline = time.monotonic() + RUN_QUEUE_TIMEOUT
    while time.monotonic() < deadline:
        run_id = capture(
            "gh",
            "run",
            "list",
            "--workflow",
            PUBLISH_WORKFLOW,
            "--branch",
            tag,
            "--limit",
            "1",
            "--json",
            "databaseId",
            "--jq",
            ".[0].databaseId // empty",
        )
        if run_id:
            return run_id
        time.sleep(RUN_POLL_INTERVAL)
    raise SystemExit(f"release: publish run for {tag} did not start within {RUN_QUEUE_TIMEOUT}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bump the version, ship, tag, and publish.")
    parser.add_argument("bump", choices=["patch", "minor", "major"])
    bump = parser.parse_args().bump

    fetch_tags()
    tags = list_tags()

    last_tag = latest_semver_tag(tags)
    if last_tag is not None:
        floor = required_bump_since(last_tag)
        if _BUMP_RANK[bump] < _BUMP_RANK[floor]:
            raise SystemExit(
                f"release: commits since {last_tag} include a feat — bump must be at least "
                f"'{floor}', got '{bump}'"
            )

    new_tag = compute_next_semver(tags, bump)
    write_pyproject_version(new_tag.removeprefix("v"))

    title = f"bump version to {new_tag.removeprefix('v')}"
    run("git-clerk", "branch", "chore/bump-version")
    run("git-clerk", "commit", "-A", title)
    run("git-clerk", "pr", title)
    run("git-clerk", "ship", "-y")
    run("git-clerk", "release", "--bump", bump, "-y")

    print(f"release: watching publish job for {new_tag}")
    run("gh", "run", "watch", wait_for_publish_run(new_tag), "--exit-status")


if __name__ == "__main__":
    main()
