import subprocess
from collections.abc import Generator
from pathlib import Path

import pytest
from click.testing import CliRunner
from pytest_subprocess import FakeProcess

from acta import github

FAKE_REPO = "test-owner/test-repo"
FAKE_REMOTE_URL = f"https://github.com/{FAKE_REPO}.git"


@pytest.fixture(autouse=True)
def clear_repo_cache() -> Generator[None, None, None]:
    github.get_repo.cache_clear()
    yield
    github.get_repo.cache_clear()


@pytest.fixture
def bare_remote(tmp_path: Path) -> Path:
    path = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(path)], check=True, capture_output=True)
    return path


@pytest.fixture
def git_repo(tmp_path: Path, bare_remote: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    local = tmp_path / "local"
    subprocess.run(["git", "clone", str(bare_remote), str(local)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=local, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=local, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=local, check=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=local, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=local, check=True)
    monkeypatch.chdir(local)
    return local


@pytest.fixture
def git_repo_with_github_remote(git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """git_repo where acta.github sees a fake GitHub URL for the origin remote.

    All real git operations (fetch, push) still target the local bare repo.
    Only get_remote_url() — the one call that feeds into gh commands — is patched.
    """

    def stub_remote_url(remote_name: str) -> str:
        return FAKE_REMOTE_URL

    monkeypatch.setattr("acta.github.get_remote_url", stub_remote_url)
    return git_repo


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def fp() -> Generator[FakeProcess, None, None]:
    """FakeProcess that passes unregistered commands (e.g., git) to the real binary."""
    with FakeProcess() as process:
        process.allow_unregistered(True)
        yield process
