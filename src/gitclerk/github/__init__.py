import functools
import subprocess
from urllib.parse import urlparse

from gitclerk.git import remote_url


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


def gh(*args: str, capture: bool = False) -> str:
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
