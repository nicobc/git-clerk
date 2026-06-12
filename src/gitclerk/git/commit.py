from gitclerk.git import git


def add_all() -> None:
    git("add", "-A")


def commit(header: str, body: str | None = None) -> None:
    args = ["commit", "-m", header]
    if body:
        args += ["-m", body]
    git(*args)


def push_head() -> None:
    git("push", "--set-upstream", "origin", "HEAD")
