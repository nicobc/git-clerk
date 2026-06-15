from pathlib import Path

import pytest
from click.testing import CliRunner
from pytest_subprocess import FakeProcess

from gitclerk.cli import main
from gitclerk.git.branch import TYPES, current_branch
from gitclerk.git.config import get_active_issue
from gitclerk.github.label import TYPE_COLORS

FAKE_REPO = "test-owner/test-repo"
MILESTONE_API = f"repos/{FAKE_REPO}/milestones"
ISSUE_FIELDS = "number,title,labels,milestone"


class TestMilestoneNew:
    def test_creates_milestone(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            [
                "gh",
                "api",
                MILESTONE_API,
                "--method",
                "POST",
                "-f",
                "title=Auth System",
                "-f",
                "description=scope: auth",
            ],
            stdout='{"number": 1}',
        )
        result = runner.invoke(main, ["milestone", "new", "Auth System", "--scope", "auth"])
        assert result.exit_code == 0, result.output
        assert result.output == "Milestone #1 created.\n"

    def test_creates_milestone_with_description(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            [
                "gh",
                "api",
                MILESTONE_API,
                "--method",
                "POST",
                "-f",
                "title=Auth System",
                "-f",
                "description=scope: auth\n\nBuild authentication.",
            ],
            stdout='{"number": 2}',
        )
        result = runner.invoke(
            main, ["milestone", "new", "Auth System", "Build authentication.", "--scope", "auth"]
        )
        assert result.exit_code == 0, result.output
        assert result.output == "Milestone #2 created.\n"


class TestMilestoneList:
    def test_lists_milestones(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", MILESTONE_API, "-X", "GET", "-f", "state=open"],
            stdout=(
                '[{"number": 1, "title": "Auth System", "description": "scope: auth",'
                ' "open_issues": 3, "closed_issues": 1}]'
            ),
        )
        result = runner.invoke(main, ["milestone", "list"])
        assert result.exit_code == 0, result.output
        assert result.output == "#1 Auth System scope: auth [3 open, 1 closed]\n"

    def test_no_milestones(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", MILESTONE_API, "-X", "GET", "-f", "state=open"],
            stdout="[]",
        )
        result = runner.invoke(main, ["milestone", "list"])
        assert result.exit_code == 0, result.output
        assert result.output == "No open milestones.\n"


class TestMilestoneReopen:
    def test_reopens_milestone(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", f"{MILESTONE_API}/1", "--method", "PATCH", "-f", "state=open"],
        )
        result = runner.invoke(main, ["milestone", "reopen", "1"])
        assert result.exit_code == 0, result.output
        assert result.output == "Milestone #1 reopened.\n"


class TestIssueNew:
    def test_creates_issue(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            [
                "gh",
                "issue",
                "create",
                "--title",
                "Add login",
                "--body",
                "",
                "--repo",
                FAKE_REPO,
                "--label",
                "type: feat",
            ],
            stdout=f"https://github.com/{FAKE_REPO}/issues/1",
        )
        result = runner.invoke(main, ["issue", "new", "Add login", "--type", "feat"])
        assert result.exit_code == 0, result.output
        assert result.output == "Issue #1 created.\n"

    def test_auto_creates_labels_on_missing_label(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        create_args = [
            "gh",
            "issue",
            "create",
            "--title",
            "Add login",
            "--body",
            "",
            "--repo",
            FAKE_REPO,
            "--label",
            "type: feat",
        ]
        fp.register(create_args, returncode=1)  # pyright: ignore[reportUnknownMemberType]
        for type_ in TYPES:
            color = TYPE_COLORS.get(type_, "ededed")
            fp.register(  # pyright: ignore[reportUnknownMemberType]
                [
                    "gh",
                    "label",
                    "create",
                    f"type: {type_}",
                    "--color",
                    color,
                    "--force",
                    "--repo",
                    FAKE_REPO,
                ],
            )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            create_args,
            stdout=f"https://github.com/{FAKE_REPO}/issues/1",
        )
        result = runner.invoke(main, ["issue", "new", "Add login", "--type", "feat"])
        assert result.exit_code == 0, result.output
        assert result.output == "Issue #1 created.\n"

    def test_creates_issue_with_type_and_milestone(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            [
                "gh",
                "issue",
                "create",
                "--title",
                "Add login",
                "--body",
                "",
                "--repo",
                FAKE_REPO,
                "--label",
                "type: feat",
                "--milestone",
                "1",
            ],
            stdout=f"https://github.com/{FAKE_REPO}/issues/2",
        )
        result = runner.invoke(
            main, ["issue", "new", "Add login", "--type", "feat", "--milestone", "1"]
        )
        assert result.exit_code == 0, result.output
        assert result.output == "Issue #2 created.\n"


class TestIssueList:
    def test_lists_issues(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "list", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS, "--state", "open"],
            stdout=(
                '[{"number": 1, "title": "Add login", "labels": [{"name": "type: feat"}],'
                ' "milestone": {"number": 1, "title": "Auth System"}}]'
            ),
        )
        result = runner.invoke(main, ["issue", "list"])
        assert result.exit_code == 0, result.output
        assert result.output == "#1 [feat] [milestone #1] Add login\n"

    def test_no_issues(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "list", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS, "--state", "open"],
            stdout="[]",
        )
        result = runner.invoke(main, ["issue", "list"])
        assert result.exit_code == 0, result.output
        assert result.output == "No open issues.\n"


class TestIssueStart:
    ISSUE_JSON = (
        '{"number": 1, "title": "Add login", "labels": [{"name": "type: feat"}],'
        ' "milestone": {"number": 1, "title": "Auth System"}}'
    )
    MILESTONE_JSON = (
        '{"number": 1, "title": "Auth System", "description": "scope: auth",'
        ' "open_issues": 1, "state": "open"}'
    )

    @pytest.fixture(autouse=True)
    def _register_gh_commands(self, fp: FakeProcess) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "1", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS],
            stdout=self.ISSUE_JSON,
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", f"{MILESTONE_API}/1"],
            stdout=self.MILESTONE_JSON,
        )

    def test_creates_branch_and_records_active_issue(
        self, git_repo_with_github_remote: Path, runner: CliRunner
    ) -> None:
        result = runner.invoke(main, ["issue", "start", "1"])
        assert result.exit_code == 0, result.output
        assert result.output == "On branch 'feat/auth', active issue is #1.\n"
        assert current_branch() == "feat/auth"
        assert get_active_issue() == 1

    def test_fails_without_milestone(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "2", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS],
            stdout=(
                '{"number": 2, "title": "No milestone",'
                ' "labels": [{"name": "type: feat"}], "milestone": null}'
            ),
        )
        result = runner.invoke(main, ["issue", "start", "2"])
        assert result.exit_code != 0
        assert result.output == (
            "Error: Issue #2 has no milestone — assign it to a milestone first\n"
        )

    def test_fails_without_scope(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "3", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS],
            stdout=(
                '{"number": 3, "title": "No scope issue",'
                ' "labels": [{"name": "type: feat"}],'
                ' "milestone": {"number": 2, "title": "No Scope"}}'
            ),
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", f"{MILESTONE_API}/2"],
            stdout=(
                '{"number": 2, "title": "No Scope",'
                ' "description": "", "open_issues": 1, "state": "open"}'
            ),
        )
        result = runner.invoke(main, ["issue", "start", "3"])
        assert result.exit_code != 0
        expected = (
            "Error: Milestone #2 has no scope — its description must start with 'scope: SCOPE'\n"
        )
        assert result.output == expected

    def test_fails_without_type_label(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "4", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS],
            stdout=(
                '{"number": 4, "title": "Unlabeled",'
                ' "labels": [],'
                ' "milestone": {"number": 1, "title": "Auth System"}}'
            ),
        )
        result = runner.invoke(main, ["issue", "start", "4"])
        assert result.exit_code != 0
        assert result.output == (
            "Error: Issue #4 has no type label — assign a 'type: TYPE' label on GitHub\n"
        )


class TestIssueDiscard:
    def test_discards_issue(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "close", "1", "--reason", "not planned", "--repo", FAKE_REPO],
        )
        result = runner.invoke(main, ["issue", "discard", "1"])
        assert result.exit_code == 0, result.output
        assert result.output == "Issue #1 discarded.\n"


class TestShipClosesMilestone:
    @pytest.fixture(autouse=True)
    def _on_feature_branch(self, git_repo_with_github_remote: Path) -> None:
        from gitclerk.git.branch import switch_new_branch
        from gitclerk.git.config import set_active_issue

        switch_new_branch("feat/auth")
        set_active_issue(1)

    @pytest.fixture(autouse=True)
    def _register_pr_commands(self, fp: FakeProcess) -> None:
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

    def test_clears_active_issue_on_ship(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "1", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS],
            stdout=(
                '{"number": 1, "title": "Add login", "labels": [{"name": "type: feat"}],'
                ' "milestone": null}'
            ),
        )
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 0, result.output
        assert result.output == ""
        assert get_active_issue() is None

    def test_closes_milestone_when_all_issues_done(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
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
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
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
