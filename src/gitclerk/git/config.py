import subprocess

from gitclerk.git import git


def get_active_issue() -> int | None:
    try:
        value = git("config", "--get", "clerk.active-issue", capture=True)
        return int(value) if value else None
    except subprocess.CalledProcessError:
        return None


def set_active_issue(number: int) -> None:
    git("config", "clerk.active-issue", str(number))


def clear_active_issue() -> None:
    try:
        git("config", "--unset", "clerk.active-issue")
    except subprocess.CalledProcessError:
        pass
