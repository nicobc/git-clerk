"""Version-tag math: detect the scheme and compute the next CalVer/SemVer tag."""

import re
from datetime import date
from typing import Final, Literal, TypeAlias

from acta.git import git
from acta.git.commit import get_commit_subjects

CALVER: Final = "CalVer"
SEMVER: Final = "SemVer"
Scheme: TypeAlias = Literal["CalVer", "SemVer"]

_CALVER_RE = re.compile(r"v\d{4}\.\d{2}\.\d+")
_SEMVER_RE = re.compile(r"v\d+\.\d+\.\d+")
_CONVENTIONAL_HEADER_RE = re.compile(r"(?P<type>\w+)(\([^)]*\))?(?P<breaking>!)?:")


def detect_scheme(existing_tags: list[str]) -> Scheme | None:
    """Infer the versioning scheme already in use from existing tags.

    Args:
        existing_tags: All version tags in the repo, e.g. ``["v2026.06.1"]``.

    Returns:
        ``"CalVer"`` or ``"SemVer"`` if exactly one scheme is present, else None
        when there are no version tags yet.

    Raises:
        ValueError: If both schemes appear, since the next tag is then ambiguous.

    Example:
        >>> detect_scheme(["v1.2.0", "v1.3.0"])
        'SemVer'
    """
    found_schemes: set[Scheme] = set()
    for tag in existing_tags:
        if _CALVER_RE.fullmatch(tag):
            found_schemes.add(CALVER)
        elif _SEMVER_RE.fullmatch(tag):
            found_schemes.add(SEMVER)
    if not found_schemes:
        return None
    if len(found_schemes) > 1:
        raise ValueError(f"mixed {CALVER} and {SEMVER} tags found — pass --scheme to proceed")
    return next(iter(found_schemes))


def compute_next_calver(existing_tags: list[str], today: date) -> str:
    """Compute the next CalVer tag ``vYYYY.MM.N`` for today's month.

    N is the count of releases already cut this month plus one, so the first
    release in a month is ``.1`` and subsequent ones increment.

    Args:
        existing_tags: All version tags in the repo.
        today: The date the release is being cut.

    Returns:
        The next CalVer tag.

    Example:
        >>> compute_next_calver(["v2026.06.1"], date(2026, 6, 23))
        'v2026.06.2'
    """
    prefix = f"v{today.year}.{today.month:02d}."
    month_tags = [tag for tag in existing_tags if re.fullmatch(rf"{re.escape(prefix)}\d+", tag)]
    last_counter = max((int(tag[len(prefix) :]) for tag in month_tags), default=0)
    return f"{prefix}{last_counter + 1}"


def latest_semver_tag(existing_tags: list[str]) -> str | None:
    """Return the highest SemVer tag by numeric precedence, or None if there are none.

    Example:
        >>> latest_semver_tag(["v1.9.0", "v1.10.0", "v1.2.0"])
        'v1.10.0'
    """
    semver_tags = sorted(
        (
            tag
            for tag in existing_tags
            if _SEMVER_RE.fullmatch(tag) and not _CALVER_RE.fullmatch(tag)
        ),
        key=lambda tag: tuple(int(part) for part in tag[1:].split(".")),
    )
    return semver_tags[-1] if semver_tags else None


def semver_major(tag: str) -> int:
    """Return the major-version number from a SemVer tag (``v2.3.1`` → ``2``)."""
    return int(tag[1:].split(".")[0])


def derive_bump(commit_subjects: list[str], current_major: int) -> str:
    """Derive the SemVer bump from the conventional-commit subjects since the last release.

    A `!` breaking marker bumps major once stable (1.0+); while still 0.x it is capped at
    minor, since a pre-1.0 breaking change must not force 1.0.0 — that is the deliberate
    `--stable` decision. A `feat` bumps minor; anything else, patch.

    Args:
        commit_subjects: Commit subject lines since the last tag.
        current_major: Major version of the latest release (0 before the first).

    Returns:
        One of ``"major"``, ``"minor"``, ``"patch"``.

    Example:
        >>> derive_bump(["feat(api): add endpoint", "fix: typo"], current_major=1)
        'minor'
    """
    has_breaking = False
    has_feat = False
    for subject in commit_subjects:
        header = _CONVENTIONAL_HEADER_RE.match(subject)
        if header is None:
            continue
        has_breaking = has_breaking or header.group("breaking") is not None
        has_feat = has_feat or header.group("type") == "feat"
    if has_breaking and current_major >= 1:
        return "major"
    if has_breaking or has_feat:
        return "minor"
    return "patch"


def compute_next_semver(existing_tags: list[str], bump: str) -> str:
    """Apply a ``major``/``minor``/``patch`` bump to the latest SemVer tag.

    Defaults to ``v0.1.0`` when no SemVer tag exists yet. A major bump zeroes
    minor and patch; a minor bump zeroes patch.

    Example:
        >>> compute_next_semver(["v1.4.2"], "minor")
        'v1.5.0'
    """
    latest = latest_semver_tag(existing_tags)
    if latest is None:
        return "v0.1.0"
    major, minor, patch = (int(part) for part in latest[1:].split("."))
    if bump == "major":
        return f"v{major + 1}.0.0"
    if bump == "minor":
        return f"v{major}.{minor + 1}.0"
    return f"v{major}.{minor}.{patch + 1}"


def next_release_tag(existing_tags: list[str], stable: bool) -> str:
    """The next SemVer tag: a deliberate v1.0.0 with `stable`, else derived from commits.

    Args:
        existing_tags: All version tags in the repo.
        stable: Promote a 0.x project straight to v1.0.0.

    Returns:
        The next SemVer tag.

    Raises:
        ValueError: If `stable` is requested on an already-stable (1.0+) project.
    """
    latest = latest_semver_tag(existing_tags)
    if stable:
        if latest is not None and semver_major(latest) >= 1:
            raise ValueError("--stable only promotes 0.x to v1.0.0; this project is already stable")
        return "v1.0.0"
    current_major = semver_major(latest) if latest is not None else 0
    subjects = get_commit_subjects(f"{latest}..origin/main") if latest is not None else []
    return compute_next_semver(existing_tags, derive_bump(subjects, current_major))


def fetch_tags() -> None:
    """Download all tags from origin."""
    git("fetch", "--tags", "origin", quiet=True)


def list_tags(pattern: str = "v*") -> list[str]:
    """Return local tags matching ``pattern`` (default: all ``v*`` version tags)."""
    return [tag for tag in git("tag", "--list", pattern, capture=True).splitlines() if tag]


def create_tag(tag: str, ref: str = "origin/main") -> None:
    """Create ``tag`` at ``ref`` and push it to origin, which fires the publish workflow.

    Args:
        tag: The tag to create, e.g. ``v1.2.0``.
        ref: The commit-ish to tag (default: the tip of origin/main).

    Raises:
        RuntimeError: If the tag already exists locally.
    """
    if tag in list_tags():
        raise RuntimeError(
            f"tag '{tag}' already exists — re-run 'acta release' to get the next version"
        )
    git("tag", tag, ref, quiet=True)
    git("push", "origin", tag, quiet=True)
