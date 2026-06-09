import functools
import json
import subprocess
from urllib.parse import urlparse

from git_clerk.git import remote_url


def parse_repo_from_url(url: str) -> str:
    if "://" in url:
        path = urlparse(url).path.lstrip("/")
    else:
        _, _, path = url.partition(":")
    repo = path.removesuffix(".git")
    parts = repo.split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"cannot parse GitHub repo from remote URL: {url}")
    return repo


def _gh(*args: str, capture: bool = False) -> str:
    try:
        result = subprocess.run(
            ["gh", *args],
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture else None,
        )
        return result.stdout.strip() if result.stdout else ""
    except FileNotFoundError:
        raise RuntimeError(
            "'gh' not found in PATH — install the GitHub CLI: https://cli.github.com"
        )
    except subprocess.CalledProcessError:
        raise


@functools.cache
def repo() -> str:
    url = remote_url("origin")
    try:
        return parse_repo_from_url(url)
    except ValueError as e:
        raise RuntimeError(str(e)) from e


def pr_create(title: str, body: str, base: str = "main") -> tuple[int, str]:
    args = [
        "pr", "create", "--base", base, "--title", title, "--repo", repo(), "--json", "number,url"
    ]
    if body:
        args += ["--body", body]
    out = _gh(*args, capture=True)
    data = json.loads(out)
    return int(data["number"]), str(data["url"])


def pr_view() -> tuple[int, str]:
    out = _gh("pr", "view", "--repo", repo(), "--json", "number,title", capture=True)
    data = json.loads(out)
    return int(data["number"]), str(data["title"])


def pr_checks_pass(pr_number: int) -> bool:
    try:
        _gh("pr", "checks", str(pr_number), "--repo", repo(), capture=True)
        return True
    except subprocess.CalledProcessError:
        return False


def pr_merge(pr_number: int) -> None:
    _gh("pr", "merge", str(pr_number), "--squash", "--delete-branch", "--repo", repo())


def pr_checks_watch(pr_number: int) -> None:
    _gh("pr", "checks", str(pr_number), "--repo", repo(), "--watch")
