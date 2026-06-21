from gitclerk.git import git


def add_all() -> None:
    git("add", "-A")


def commit(header: str, body: str | None = None) -> None:
    commit_args = ["commit", "-m", header]
    if body:
        commit_args += ["-m", body]
    git(*commit_args)


def push_head() -> None:
    git("push", "--set-upstream", "origin", "HEAD", quiet=True)


def commit_subjects(rev_range: str) -> list[str]:
    return git("log", rev_range, "--format=%s", capture=True).splitlines()
