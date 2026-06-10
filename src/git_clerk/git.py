import subprocess


def _git(*args: str, capture: bool = False) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture else None,
        )
        return result.stdout.strip() if result.stdout else ""
    except FileNotFoundError:
        raise RuntimeError("'git' not found in PATH — install git: https://git-scm.com/install/")
    except subprocess.CalledProcessError:
        raise


def current_branch() -> str:
    return _git("branch", "--show-current", capture=True)


def fetch_origin() -> None:
    _git("fetch", "origin")


def fetch_tags() -> None:
    _git("fetch", "--tags", "origin")


def switch_new_branch(name: str) -> None:
    _git("switch", "-c", name, "origin/main")


def switch_main() -> None:
    _git("switch", "main")


def pull_origin_main() -> None:
    _git("pull", "origin", "main")


def branch_exists(name: str) -> bool:
    return bool(_git("branch", "--list", name, capture=True))


def delete_branch(name: str) -> None:
    _git("branch", "-D", name)


def switch_branch(name: str) -> None:
    _git("switch", name)


def merge_origin_main() -> None:
    _git("merge", "origin/main")


def add_all() -> None:
    _git("add", "-A")


def commit(header: str, body: str | None = None) -> None:
    args = ["commit", "-m", header]
    if body:
        args += ["-m", body]
    _git(*args)


def push_head() -> None:
    _git("push", "--set-upstream", "origin", "HEAD")


def remote_url(name: str) -> str:
    return _git("remote", "get-url", name, capture=True)


def tags(pattern: str = "v*") -> list[str]:
    return [t for t in _git("tag", "--list", pattern, capture=True).splitlines() if t]


def create_tag(tag: str, ref: str = "origin/main") -> None:
    if tag in tags():
        raise RuntimeError(
            f"tag '{tag}' already exists — re-run 'git clerk release' to get the next version"
        )
    _git("tag", tag, ref)
    _git("push", "origin", tag)
