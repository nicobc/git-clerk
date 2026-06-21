import functools
import subprocess
from urllib.parse import urlparse

from acta.git import get_remote_url


def parse_repo_from_url(url: str) -> str:
    if "://" in url:
        path = urlparse(url).path.lstrip("/")
    else:
        _, _, path = url.partition(":")
    repo_slug = path.removesuffix(".git")
    repo_parts = repo_slug.split("/")
    if len(repo_parts) != 2 or not all(repo_parts):
        raise ValueError(f"cannot parse GitHub repo from remote URL: {url}")
    return repo_slug


def gh(*args: str, capture: bool = False) -> str:
    try:
        completed_process = subprocess.run(
            ["gh", *args],
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture else None,
        )
        return completed_process.stdout.strip() if completed_process.stdout else ""
    except FileNotFoundError:
        raise RuntimeError(
            "'gh' not found in PATH — install the GitHub CLI: https://cli.github.com"
        )
    except subprocess.CalledProcessError:
        raise


@functools.cache
def get_repo() -> str:
    origin_url = get_remote_url("origin")
    try:
        return parse_repo_from_url(origin_url)
    except ValueError as error:
        raise RuntimeError(str(error)) from error
