import re
from datetime import date
from typing import Final, Literal, TypeAlias

from gitclerk.git import git

CALVER: Final = "CalVer"
SEMVER: Final = "SemVer"
Scheme: TypeAlias = Literal["CalVer", "SemVer"]

_CALVER_RE = re.compile(r"v\d{4}\.\d{2}\.\d+")
_SEMVER_RE = re.compile(r"v\d+\.\d+\.\d+")


def detect_scheme(existing: list[str]) -> Scheme | None:
    found: set[Scheme] = set()
    for t in existing:
        if _CALVER_RE.fullmatch(t):
            found.add(CALVER)
        elif _SEMVER_RE.fullmatch(t):
            found.add(SEMVER)
    if not found:
        return None
    if len(found) > 1:
        raise ValueError(
            f"mixed {CALVER} and {SEMVER} tags found — pass --calver or --semver to proceed"
        )
    return next(iter(found))


def next_calver(existing: list[str], today: date) -> str:
    prefix = f"v{today.year}.{today.month:02d}."
    month_tags = [t for t in existing if re.fullmatch(rf"{re.escape(prefix)}\d+", t)]
    last = max((int(t[len(prefix) :]) for t in month_tags), default=0)
    return f"{prefix}{last + 1}"


def next_semver(existing: list[str], bump: str) -> str:
    semver_tags = sorted(
        [t for t in existing if _SEMVER_RE.fullmatch(t) and not _CALVER_RE.fullmatch(t)],
        key=lambda t: tuple(int(x) for x in t[1:].split(".")),
    )
    if not semver_tags:
        return "v0.1.0"
    major, minor, patch = (int(x) for x in semver_tags[-1][1:].split("."))
    if bump == "major":
        return f"v{major + 1}.0.0"
    if bump == "minor":
        return f"v{major}.{minor + 1}.0"
    return f"v{major}.{minor}.{patch + 1}"


def fetch_tags() -> None:
    git("fetch", "--tags", "origin")


def tags(pattern: str = "v*") -> list[str]:
    return [t for t in git("tag", "--list", pattern, capture=True).splitlines() if t]


def create_tag(tag: str, ref: str = "origin/main") -> None:
    if tag in tags():
        raise RuntimeError(
            f"tag '{tag}' already exists — re-run 'git clerk release' to get the next version"
        )
    git("tag", tag, ref)
    git("push", "origin", tag)
