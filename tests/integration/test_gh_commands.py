import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner
from pytest_subprocess import FakeProcess

from git_clerk import git
from git_clerk.cli import main

FAKE_REPO = "test-owner/test-repo"
PR_URL = f"https://github.com/{FAKE_REPO}/pull/1"


class TestPr:
    @pytest.fixture(autouse=True)
    def _on_feature_branch(self, git_repo_with_github_remote: Path) -> None:
        git.switch_new_branch("feat/my-scope")
        (git_repo_with_github_remote / "file.txt").write_text("hello")
        git.add_all()
        git.commit("feat(my-scope): add something")

    @pytest.fixture(autouse=True)
    def _register_gh_commands(self, fp: FakeProcess) -> None:
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

    def test_pushes_branch_and_creates_pr(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["pr", "add tests"])
        assert result.exit_code == 0, result.output
        assert PR_URL in result.output


class TestShip:
    @pytest.fixture(autouse=True)
    def _on_feature_branch(self, git_repo_with_github_remote: Path) -> None:
        git.switch_new_branch("feat/my-scope")

    @pytest.fixture
    def _create_other_branch(self, git_repo_with_github_remote: Path) -> None:
        subprocess.run(
            ["git", "branch", "feat/other", "origin/main"],
            cwd=git_repo_with_github_remote,
            check=True,
        )

    @pytest.fixture(autouse=True)
    def _register_gh_commands(self, fp: FakeProcess) -> None:
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

    def test_merges_pr_and_returns_to_main(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 0, result.output
        assert git.current_branch() == "main"
        assert not git.branch_exists("feat/my-scope")

    @pytest.mark.usefixtures("_create_other_branch")
    def test_switches_to_update_branch_after_ship(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["ship", "-y", "--update", "feat/other"])
        assert result.exit_code == 0, result.output
        assert git.current_branch() == "feat/other"


class TestShipChecksFailure:
    @pytest.fixture(autouse=True)
    def _on_feature_branch(self, git_repo_with_github_remote: Path) -> None:
        git.switch_new_branch("feat/my-scope")

    @pytest.fixture(autouse=True)
    def _register_gh_commands(self, fp: FakeProcess) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "view", "feat/my-scope", "--repo", FAKE_REPO, "--json", "number,title"],
            stdout='{"number": 1, "title": "feat(my-scope): add something"}',
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "checks", "1", "--repo", FAKE_REPO],
            returncode=1,
        )

    def test_fails_if_checks_failing(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code != 0


class TestShipFromMain:
    def test_fails_when_on_main(self, git_repo_with_github_remote: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code != 0
        assert "feature branch" in result.output


class TestWatch:
    @pytest.fixture(autouse=True)
    def _on_feature_branch(self, git_repo_with_github_remote: Path) -> None:
        git.switch_new_branch("feat/my-scope")

    @pytest.fixture(autouse=True)
    def _register_gh_commands(self, fp: FakeProcess) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "view", "feat/my-scope", "--repo", FAKE_REPO, "--json", "number,title"],
            stdout='{"number": 1, "title": "feat(my-scope): add something"}',
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "view", "1", "--repo", FAKE_REPO, "--json", "statusCheckRollup"],
            stdout='{"statusCheckRollup": [{"state": "SUCCESS"}]}',
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "checks", "1", "--repo", FAKE_REPO, "--watch"],
        )

    def test_watches_ci_for_current_pr(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["watch"])
        assert result.exit_code == 0, result.output
