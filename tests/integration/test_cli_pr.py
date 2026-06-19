import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner
from pytest_subprocess import FakeProcess

from gitclerk.cli import main
from gitclerk.git.branch import branch_exists, current_branch, switch_main, switch_new_branch
from gitclerk.git.commit import add_all
from gitclerk.git.commit import commit as git_commit
from gitclerk.git.config import get_active_issue, set_active_issue

FAKE_REPO = "test-owner/test-repo"
MILESTONE_API = f"repos/{FAKE_REPO}/milestones"
ISSUE_FIELDS = "number,title,labels,milestone"
PR_URL = f"https://github.com/{FAKE_REPO}/pull/1"


class TestPr:
    @pytest.fixture(autouse=True)
    def _setup(self, git_repo_with_github_remote: Path, fp: FakeProcess) -> None:
        switch_new_branch("feat/my-scope")
        (git_repo_with_github_remote / "file.txt").write_text("hello")
        add_all()
        git_commit("feat(my-scope): add something")
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            [
                "gh",
                "pr",
                "create",
                "--base",
                "main",
                "--title",
                "feat(my-scope): add tests",
                "--body",
                "",
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
    def _on_feature_branch(self, git_repo_with_github_remote: Path, fp: FakeProcess) -> None:
        switch_new_branch("feat/my-scope")
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "view", "feat/my-scope", "--repo", FAKE_REPO, "--json", "number,title"],
            stdout='{"number": 1, "title": "feat(my-scope): add something"}',
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "merge", "1", "--squash", "--delete-branch", "--repo", FAKE_REPO],
        )

    @pytest.fixture
    def _checks_pass(self, fp: FakeProcess) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "checks", "1", "--repo", FAKE_REPO],
            stdout="All checks pass",
        )

    @pytest.fixture
    def _on_main(self) -> None:
        switch_main()

    @pytest.mark.usefixtures("_checks_pass")
    def test_merges_pr_and_returns_to_main(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 0, result.output
        assert current_branch() == "main"
        assert not branch_exists("feat/my-scope")

    @pytest.mark.usefixtures("_checks_pass")
    def test_switches_to_update_branch_after_ship(
        self, git_repo_with_github_remote: Path, runner: CliRunner
    ) -> None:
        subprocess.run(
            ["git", "branch", "feat/other", "origin/main"],
            cwd=git_repo_with_github_remote,
            check=True,
        )
        result = runner.invoke(main, ["ship", "-y", "--update", "feat/other"])
        assert result.exit_code == 0, result.output
        assert current_branch() == "feat/other"

    def test_ships_when_no_checks_reported(self, runner: CliRunner, fp: FakeProcess) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "checks", "1", "--repo", FAKE_REPO],
            returncode=1,
            stderr="no checks reported on the 'feat/my-scope' branch",
        )
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 0, result.output

    def test_fails_if_checks_failing(self, runner: CliRunner, fp: FakeProcess) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "checks", "1", "--repo", FAKE_REPO],
            returncode=1,
            stderr="some checks are failing",
        )
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 1
        assert "failing or pending checks" in result.output

    @pytest.mark.usefixtures("_on_main")
    def test_fails_when_on_main(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 1
        assert "feature branch" in result.output


class TestShipWithMilestone:
    @pytest.fixture(autouse=True)
    def _setup(self, git_repo_with_github_remote: Path, fp: FakeProcess) -> None:
        switch_new_branch("feat/auth")
        set_active_issue(1)
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "view", "feat/auth", "--repo", FAKE_REPO, "--json", "number,title"],
            stdout='{"number": 1, "title": "feat(auth): add login"}',
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "checks", "1", "--repo", FAKE_REPO],
            stdout="All checks pass",
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "merge", "1", "--squash", "--delete-branch", "--repo", FAKE_REPO],
        )

    def test_clears_active_issue_on_ship(self, runner: CliRunner, fp: FakeProcess) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "1", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS],
            stdout=(
                '{"number": 1, "title": "Add login", "labels": [{"name": "type: feat"}],'
                ' "milestone": null}'
            ),
        )
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 0, result.output
        assert get_active_issue() is None

    def test_closes_milestone_when_all_issues_done(
        self, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "1", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS],
            stdout=(
                '{"number": 1, "title": "Add login", "labels": [{"name": "type: feat"}],'
                ' "milestone": {"number": 1, "title": "Auth System"}}'
            ),
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", f"{MILESTONE_API}/1"],
            stdout=(
                '{"number": 1, "title": "Auth System", "description": "scope: auth",'
                ' "open_issues": 0, "state": "open"}'
            ),
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", f"{MILESTONE_API}/1", "--method", "PATCH", "-f", "state=closed"],
        )
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 0, result.output
        assert result.output == 'Milestone #1 "Auth System" completed and closed.\n'

    def test_does_not_close_milestone_with_open_issues(
        self, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "1", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS],
            stdout=(
                '{"number": 1, "title": "Add login", "labels": [{"name": "type: feat"}],'
                ' "milestone": {"number": 1, "title": "Auth System"}}'
            ),
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", f"{MILESTONE_API}/1"],
            stdout=(
                '{"number": 1, "title": "Auth System", "description": "scope: auth",'
                ' "open_issues": 2, "state": "open"}'
            ),
        )
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 0, result.output
        assert result.output == ""


class TestWatch:
    @pytest.fixture(autouse=True)
    def _setup(self, git_repo_with_github_remote: Path, fp: FakeProcess) -> None:
        switch_new_branch("feat/my-scope")
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


class TestWatchNoCi:
    @pytest.fixture(autouse=True)
    def _setup(self, git_repo_with_github_remote: Path, fp: FakeProcess) -> None:
        switch_new_branch("feat/my-scope")
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "view", "feat/my-scope", "--repo", FAKE_REPO, "--json", "number,title"],
            stdout='{"number": 1, "title": "feat(my-scope): add something"}',
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "view", "1", "--repo", FAKE_REPO, "--json", "statusCheckRollup"],
            stdout='{"statusCheckRollup": null}',
        )

    def test_returns_immediately_when_no_checks(self, runner: CliRunner, fp: FakeProcess) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "checks", "1", "--repo", FAKE_REPO],
            returncode=1,
            stderr="no checks reported on the 'feat/my-scope' branch",
        )
        result = runner.invoke(main, ["watch"])
        assert result.exit_code == 0, result.output

    def test_watches_when_checks_pass_during_polling(
        self, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "checks", "1", "--repo", FAKE_REPO],
            stdout="All checks pass",
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "checks", "1", "--repo", FAKE_REPO, "--watch"],
        )
        result = runner.invoke(main, ["watch"])
        assert result.exit_code == 0, result.output
