import json
import subprocess
import time

from gitclerk.git.branch import current_branch
from gitclerk.github import gh, repo

_CHECKS_POLL_INTERVAL = 5  # seconds
_CHECKS_QUEUE_TIMEOUT = 90  # seconds to wait for checks to appear


def pr_create(title: str, body: str, base: str = "main") -> tuple[int, str]:
    args = ["pr", "create", "--base", base, "--title", title, "--body", body, "--repo", repo()]
    url = gh(*args, capture=True)
    number = int(url.rstrip("/").split("/")[-1])
    return number, url


def pr_view() -> tuple[int, str]:
    out = gh(
        "pr", "view", current_branch(), "--repo", repo(), "--json", "number,title", capture=True
    )
    data = json.loads(out)
    return int(data["number"]), str(data["title"])


def pr_checks_pass(pr_number: int) -> bool:
    try:
        subprocess.run(
            ["gh", "pr", "checks", str(pr_number), "--repo", repo()],
            check=True,
            text=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        if "no checks reported" in (e.stderr or ""):
            print(e.stderr.strip())
            return True
        return False


def pr_merge(pr_number: int) -> None:
    gh("pr", "merge", str(pr_number), "--squash", "--delete-branch", "--repo", repo())


def pr_checks_watch(pr_number: int) -> None:
    for _ in range(_CHECKS_QUEUE_TIMEOUT // _CHECKS_POLL_INTERVAL):
        out = gh(
            "pr",
            "view",
            str(pr_number),
            "--repo",
            repo(),
            "--json",
            "statusCheckRollup",
            capture=True,
        )
        if json.loads(out).get("statusCheckRollup"):
            break
        try:
            subprocess.run(
                ["gh", "pr", "checks", str(pr_number), "--repo", repo()],
                check=True,
                text=True,
                capture_output=True,
            )
            break
        except subprocess.CalledProcessError as e:
            if "no checks reported" in (e.stderr or ""):
                print(e.stderr.strip())
                return
        time.sleep(_CHECKS_POLL_INTERVAL)
    gh("pr", "checks", str(pr_number), "--repo", repo(), "--watch")
