import subprocess


def git(*args: str, capture: bool = False, quiet: bool = False) -> str:
    """Run a git command.

    `capture` returns stdout. `quiet` suppresses stdout and stderr on success; on
    failure the captured stderr rides along on the raised CalledProcessError so the
    error is still surfaced (see CLIGroup).
    """
    try:
        completed_process = subprocess.run(
            ["git", *args],
            check=True,
            text=True,
            stdout=subprocess.PIPE if (capture or quiet) else None,
            stderr=subprocess.PIPE if quiet else None,
        )
        return completed_process.stdout.strip() if completed_process.stdout else ""
    except FileNotFoundError:
        raise RuntimeError("'git' not found in PATH — install git: https://git-scm.com/install/")
    except subprocess.CalledProcessError:
        raise


def get_remote_url(remote_name: str) -> str:
    return git("remote", "get-url", remote_name, capture=True)
