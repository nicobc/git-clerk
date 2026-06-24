"""Staging, committing, and pushing helpers."""

from acta.git import git


def add_all() -> None:
    """Stage every change in the working tree (tracked, new, and deleted)."""
    git("add", "-A")


def commit(header: str, body: str | None = None) -> None:
    """Create a commit with ``header`` as the subject and an optional ``body`` paragraph."""
    commit_args = ["commit", "-m", header]
    if body:
        commit_args += ["-m", body]
    git(*commit_args)


def push_head() -> None:
    """Push the current branch to origin, setting it as the upstream to track."""
    git("push", "--set-upstream", "origin", "HEAD", quiet=True)


def get_commit_subjects(rev_range: str) -> list[str]:
    """Return the subject line of each commit in ``rev_range`` (e.g. ``v1.0.0..origin/main``)."""
    return git("log", rev_range, "--format=%s", capture=True).splitlines()


def get_working_tree_changes() -> list[str]:
    """Return ``git status --porcelain`` lines for the working tree, empty if clean.

    Each line is a two-character status code and a path, e.g. ``" M src/app.py"``
    (modified, unstaged) or ``"?? new.py"`` (untracked).
    """
    return git("status", "--porcelain", capture=True).splitlines()
