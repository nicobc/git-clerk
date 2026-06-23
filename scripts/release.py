#!/usr/bin/env python3
"""Cut a git-acta release: bump the version, ship it, tag it, and watch the publish job.

Maintainer-only — this script is not part of the published package. Run from the repo root:

    uv run scripts/release.py            # version derived from commits since the last tag
    uv run scripts/release.py --stable   # one-time promotion of a 0.x project to v1.0.0

Git tags are the source of truth for the version; pyproject.toml is overwritten to mirror
the new tag. The tag is computed with the same function `acta release` uses, so the
script and the tag it pushes always agree.
"""

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

from acta.git.commit import commit_subjects
from acta.git.tag import fetch_tags, latest_semver_tag, list_tags, next_release_tag

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
PUBLISH_WORKFLOW = "publish.yml"
RUN_POLL_INTERVAL = 5  # seconds between checks for the publish run to appear
RUN_QUEUE_TIMEOUT = 60  # give up if the publish run has not appeared within this many seconds

_VERSION_RE = re.compile(r'^version = ".*"', re.MULTILINE)


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


def wait_for_publish_run(tag: str, commit_sha: str) -> str:
    """Poll until the publish run for `tag` at `commit_sha` appears, then return its id.

    Matching the commit SHA, not just the tag name, avoids latching onto a stale run from
    an earlier push of the same tag (e.g. a deleted-and-recreated tag).
    """
    deadline = time.monotonic() + RUN_QUEUE_TIMEOUT
    while time.monotonic() < deadline:
        runs_json = capture(
            "gh",
            "run",
            "list",
            "--workflow",
            PUBLISH_WORKFLOW,
            "--branch",
            tag,
            "--limit",
            "10",
            "--json",
            "databaseId,headSha",
        )
        runs: list[dict[str, object]] = json.loads(runs_json)
        for run in runs:
            if run["headSha"] == commit_sha:
                return str(run["databaseId"])
        time.sleep(RUN_POLL_INTERVAL)
    raise SystemExit(
        f"release: publish run for {tag} ({commit_sha[:7]}) did not start "
        f"within {RUN_QUEUE_TIMEOUT}s"
    )


def _describe_bump(latest: str | None, new_tag: str) -> str:
    """Describe the jump from ``latest`` to ``new_tag`` as major/minor/patch."""
    if latest is None:
        return "initial release"
    old_major, old_minor, _ = (int(part) for part in latest[1:].split("."))
    new_major, new_minor, _ = (int(part) for part in new_tag[1:].split("."))
    if new_major > old_major:
        return "major"
    if new_minor > old_minor:
        return "minor"
    return "patch"


def main() -> None:
    parser = argparse.ArgumentParser(description="Derive the version, ship, tag, and publish.")
    parser.add_argument(
        "--stable", action="store_true", help="Promote a 0.x project to v1.0.0 (one-time)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the version and steps without changing anything.",
    )
    args = parser.parse_args()
    stable: bool = args.stable
    dry_run: bool = args.dry_run

    fetch_tags()
    existing_tags = list_tags()
    try:
        new_tag = next_release_tag(existing_tags, stable)
    except ValueError as error:
        raise SystemExit(f"release: {error}")
    new_version = new_tag.removeprefix("v")
    title = f"bump version to {new_version}"

    if dry_run:
        latest = latest_semver_tag(existing_tags)
        print("release: dry run — no changes made")
        print(f"  current version: {latest or '(none)'}")
        if latest is not None:
            print(f"  commits since {latest}:")
            for subject in commit_subjects(f"{latest}..origin/main"):
                print(f"    {subject}")
        print(f"  bump: {_describe_bump(latest, new_tag)} → {new_tag}")
        print(f"  on a real run: ship the bump, push {new_tag}, and publish to PyPI")
        return

    write_pyproject_version(new_version)
    run("uv", "lock")  # keep uv.lock's self-version in sync so the bump commit carries it

    run("acta", "branch", "chore/bump-version")
    run("acta", "commit", "-A", title)
    run("acta", "pr", title)
    run("acta", "ship", "-y")
    run("acta", "release", *(["--stable"] if stable else []), "-y")

    commit_sha = capture("git", "rev-parse", new_tag)
    print(f"release: watching publish job for {new_tag}")
    run("gh", "run", "watch", wait_for_publish_run(new_tag, commit_sha), "--exit-status")


if __name__ == "__main__":
    main()
