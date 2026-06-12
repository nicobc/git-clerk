import subprocess


def git(*args: str, capture: bool = False) -> str:
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


def remote_url(name: str) -> str:
    return git("remote", "get-url", name, capture=True)
