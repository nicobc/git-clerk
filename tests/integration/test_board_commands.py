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


class TestBoardSetup:
    @pytest.fixture(autouse=True)
    def _register_gh_commands(self, fp: FakeProcess) -> None:
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

    def test_creates_type_labels(
        self, git_repo_with_github_remote: Path, runner: CliRunner
    ) -> None:
        result = runner.invoke(main, ["board", "setup"])
        assert result.exit_code == 0, result.output
        assert result.output == "Board labels ready.\n"


class TestEpicNew:
    def test_creates_epic(
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
                "title=Auth Epic",
                "-f",
                "description=scope: auth",
            ],
            stdout='{"number": 1}',
        )
        result = runner.invoke(main, ["epic", "new", "Auth Epic", "--scope", "auth"])
        assert result.exit_code == 0, result.output
        assert result.output == "Epic #1 created.\n"

    def test_creates_epic_with_description(
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
                "title=Auth Epic",
                "-f",
                "description=scope: auth\n\nBuild authentication.",
            ],
            stdout='{"number": 2}',
        )
        result = runner.invoke(
            main, ["epic", "new", "Auth Epic", "Build authentication.", "--scope", "auth"]
        )
        assert result.exit_code == 0, result.output
        assert result.output == "Epic #2 created.\n"


class TestEpicList:
    def test_lists_epics(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", MILESTONE_API, "-X", "GET", "-f", "state=open"],
            stdout=(
                '[{"number": 1, "title": "Auth Epic", "description": "scope: auth",'
                ' "open_issues": 3, "closed_issues": 1}]'
            ),
        )
        result = runner.invoke(main, ["epic", "list"])
        assert result.exit_code == 0, result.output
        expected = (
            "#1    Auth Epic                                "
            "scope: auth                 [3 open, 1 closed]\n"
        )
        assert result.output == expected

    def test_no_epics(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", MILESTONE_API, "-X", "GET", "-f", "state=open"],
            stdout="[]",
        )
        result = runner.invoke(main, ["epic", "list"])
        assert result.exit_code == 0, result.output
        assert result.output == "No open epics.\n"


class TestEpicReopen:
    def test_reopens_epic(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", f"{MILESTONE_API}/1", "--method", "PATCH", "-f", "state=open"],
        )
        result = runner.invoke(main, ["epic", "reopen", "1"])
        assert result.exit_code == 0, result.output
        assert result.output == "Epic #1 reopened.\n"


class TestTicketNew:
    def test_creates_ticket(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "create", "--title", "Add login", "--body", "", "--repo", FAKE_REPO],
            stdout=f"https://github.com/{FAKE_REPO}/issues/1",
        )
        result = runner.invoke(main, ["ticket", "new", "Add login"])
        assert result.exit_code == 0, result.output
        assert result.output == "Ticket #1 created.\n"

    def test_creates_ticket_with_type_and_epic(
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
            main, ["ticket", "new", "Add login", "--type", "feat", "--epic", "1"]
        )
        assert result.exit_code == 0, result.output
        assert result.output == "Ticket #2 created.\n"


class TestTicketList:
    def test_lists_tickets(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "list", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS, "--state", "open"],
            stdout=(
                '[{"number": 1, "title": "Add login", "labels": [{"name": "type: feat"}],'
                ' "milestone": {"number": 1, "title": "Auth Epic"}}]'
            ),
        )
        result = runner.invoke(main, ["ticket", "list"])
        assert result.exit_code == 0, result.output
        assert result.output == "#1    [feat      ] [epic #1     ] Add login\n"

    def test_no_tickets(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "list", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS, "--state", "open"],
            stdout="[]",
        )
        result = runner.invoke(main, ["ticket", "list"])
        assert result.exit_code == 0, result.output
        assert result.output == "No open tickets.\n"


class TestTicketStart:
    ISSUE_JSON = (
        '{"number": 1, "title": "Add login", "labels": [{"name": "type: feat"}],'
        ' "milestone": {"number": 1, "title": "Auth Epic"}}'
    )
    MILESTONE_JSON = (
        '{"number": 1, "title": "Auth Epic", "description": "scope: auth",'
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
        result = runner.invoke(main, ["ticket", "start", "1"])
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
                '{"number": 2, "title": "No epic",'
                ' "labels": [{"name": "type: feat"}], "milestone": null}'
            ),
        )
        result = runner.invoke(main, ["ticket", "start", "2"])
        assert result.exit_code != 0
        assert result.output == "Error: Ticket #2 has no epic — assign it to an epic first\n"

    def test_fails_without_scope(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "3", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS],
            stdout=(
                '{"number": 3, "title": "No scope ticket",'
                ' "labels": [{"name": "type: feat"}],'
                ' "milestone": {"number": 2, "title": "No Scope Epic"}}'
            ),
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", f"{MILESTONE_API}/2"],
            stdout=(
                '{"number": 2, "title": "No Scope Epic",'
                ' "description": "", "open_issues": 1, "state": "open"}'
            ),
        )
        result = runner.invoke(main, ["ticket", "start", "3"])
        assert result.exit_code != 0
        expected = "Error: Epic #2 has no scope — its description must start with 'scope: SCOPE'\n"
        assert result.output == expected

    def test_fails_without_type_label(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "4", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS],
            stdout=(
                '{"number": 4, "title": "Unlabeled",'
                ' "labels": [],'
                ' "milestone": {"number": 1, "title": "Auth Epic"}}'
            ),
        )
        result = runner.invoke(main, ["ticket", "start", "4"])
        assert result.exit_code != 0
        assert result.output == (
            "Error: Ticket #4 has no type label — run 'git clerk board setup' and label it\n"
        )


class TestTicketDiscard:
    def test_discards_ticket(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "close", "1", "--reason", "not planned", "--repo", FAKE_REPO],
        )
        result = runner.invoke(main, ["ticket", "discard", "1"])
        assert result.exit_code == 0, result.output
        assert result.output == "Ticket #1 discarded.\n"


class TestShipClosesEpic:
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

    def test_closes_epic_when_all_tickets_done(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "1", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS],
            stdout=(
                '{"number": 1, "title": "Add login", "labels": [{"name": "type: feat"}],'
                ' "milestone": {"number": 1, "title": "Auth Epic"}}'
            ),
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", f"{MILESTONE_API}/1"],
            stdout=(
                '{"number": 1, "title": "Auth Epic", "description": "scope: auth",'
                ' "open_issues": 0, "state": "open"}'
            ),
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", f"{MILESTONE_API}/1", "--method", "PATCH", "-f", "state=closed"],
        )
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 0, result.output
        assert result.output == 'Epic #1 "Auth Epic" completed and closed.\n'

    def test_does_not_close_epic_with_open_tickets(
        self, git_repo_with_github_remote: Path, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "1", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS],
            stdout=(
                '{"number": 1, "title": "Add login", "labels": [{"name": "type: feat"}],'
                ' "milestone": {"number": 1, "title": "Auth Epic"}}'
            ),
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", f"{MILESTONE_API}/1"],
            stdout=(
                '{"number": 1, "title": "Auth Epic", "description": "scope: auth",'
                ' "open_issues": 2, "state": "open"}'
            ),
        )
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 0, result.output
        assert result.output == ""
