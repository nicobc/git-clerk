import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner
from pytest_subprocess import FakeProcess

from git_clerk.cli import main

FAKE_REPO = "test-owner/test-repo"
PR_URL = f"https://github.com/{FAKE_REPO}/pull/1"


class TestPr:
    @pytest.fixture(autouse=True)
    def on_feature_branch(self, git_repo_with_github_remote: Path) -> None:
        subprocess.run(
            ["git", "switch", "-c", "feat/my-scope", "origin/main"],
            cwd=git_repo_with_github_remote,
            check=True,
        )
        (git_repo_with_github_remote / "file.txt").write_text("hello")
        subprocess.run(["git", "add", "file.txt"], cwd=git_repo_with_github_remote, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat(my-scope): add something"],
            cwd=git_repo_with_github_remote,
            check=True,
        )

    def test_pushes_branch_and_creates_pr(self, fp: FakeProcess, runner: CliRunner) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            [
                "gh",
                "pr",
                "create",
                "--base",
                "main",
                "--title",
                "feat(my-scope): add tests",
                "--repo",
                FAKE_REPO,
            ],
            stdout=PR_URL,
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "view", "1", "--repo", FAKE_REPO, "--json", "statusCheckRollup"],
            stdout='{"statusCheckRollup": [{"state": "SUCCESS"}]}',
        )
        fp.register(["gh", "pr", "checks", "1", "--repo", FAKE_REPO, "--watch"])  # pyright: ignore[reportUnknownMemberType]
        result = runner.invoke(main, ["pr", "add tests"])
        assert result.exit_code == 0, result.output
        assert PR_URL in result.output


class TestShip:
    @pytest.fixture(autouse=True)
    def on_feature_branch(self, git_repo_with_github_remote: Path) -> None:
        subprocess.run(
            ["git", "switch", "-c", "feat/my-scope", "origin/main"],
            cwd=git_repo_with_github_remote,
            check=True,
        )

    def test_merges_pr_and_returns_to_main(
        self, git_repo_with_github_remote: Path, fp: FakeProcess, runner: CliRunner
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "view", "feat/my-scope", "--repo", FAKE_REPO, "--json", "number,title"],
            stdout='{"number": 1, "title": "feat(my-scope): add something"}',
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "checks", "1", "--repo", FAKE_REPO],
            stdout="All checks pass",
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "merge", "1", "--squash", "--delete-branch", "--repo", FAKE_REPO],
        )
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 0, result.output
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            cwd=git_repo_with_github_remote,
        ).stdout.strip()
        assert branch == "main"
        local_branches = subprocess.run(
            ["git", "branch"],
            capture_output=True,
            text=True,
            cwd=git_repo_with_github_remote,
        ).stdout
        assert "feat/my-scope" not in local_branches

    def test_fails_if_checks_failing(self, fp: FakeProcess, runner: CliRunner) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "view", "feat/my-scope", "--repo", FAKE_REPO, "--json", "number,title"],
            stdout='{"number": 1, "title": "feat(my-scope): add something"}',
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "checks", "1", "--repo", FAKE_REPO],
            returncode=1,
        )
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code != 0
