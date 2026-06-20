import re
from datetime import date
from typing import Final, Literal, TypeAlias

from gitclerk.git import git

CALVER: Final = "CalVer"
SEMVER: Final = "SemVer"
Scheme: TypeAlias = Literal["CalVer", "SemVer"]

_CALVER_RE = re.compile(r"v\d{4}\.\d{2}\.\d+")
_SEMVER_RE = re.compile(r"v\d+\.\d+\.\d+")


def detect_scheme(existing_tags: list[str]) -> Scheme | None:
    found_schemes: set[Scheme] = set()
    for tag in existing_tags:
        if _CALVER_RE.fullmatch(tag):
            found_schemes.add(CALVER)
        elif _SEMVER_RE.fullmatch(tag):
            found_schemes.add(SEMVER)
    if not found_schemes:
        return None
    if len(found_schemes) > 1:
        raise ValueError(
            f"mixed {CALVER} and {SEMVER} tags found — pass --calver or --semver to proceed"
        )
    return next(iter(found_schemes))


def compute_next_calver(existing_tags: list[str], today: date) -> str:
    prefix = f"v{today.year}.{today.month:02d}."
    month_tags = [tag for tag in existing_tags if re.fullmatch(rf"{re.escape(prefix)}\d+", tag)]
    last_counter = max((int(tag[len(prefix) :]) for tag in month_tags), default=0)
    return f"{prefix}{last_counter + 1}"


def latest_semver_tag(existing_tags: list[str]) -> str | None:
    semver_tags = sorted(
        (
            tag
            for tag in existing_tags
            if _SEMVER_RE.fullmatch(tag) and not _CALVER_RE.fullmatch(tag)
        ),
        key=lambda tag: tuple(int(part) for part in tag[1:].split(".")),
    )
    return semver_tags[-1] if semver_tags else None


def compute_next_semver(existing_tags: list[str], bump: str) -> str:
    latest = latest_semver_tag(existing_tags)
    if latest is None:
        return "v0.1.0"
    major, minor, patch = (int(part) for part in latest[1:].split("."))
    if bump == "major":
        return f"v{major + 1}.0.0"
    if bump == "minor":
        return f"v{major}.{minor + 1}.0"
    return f"v{major}.{minor}.{patch + 1}"


def fetch_tags() -> None:
    git("fetch", "--tags", "origin")


def list_tags(pattern: str = "v*") -> list[str]:
    return [tag for tag in git("tag", "--list", pattern, capture=True).splitlines() if tag]


def create_tag(tag: str, ref: str = "origin/main") -> None:
    if tag in list_tags():
        raise RuntimeError(
            f"tag '{tag}' already exists — re-run 'git clerk release' to get the next version"
        )
    git("tag", tag, ref)
    git("push", "origin", tag)
