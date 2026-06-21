from collections.abc import Callable

import pytest
from click.testing import CliRunner
from pytest_subprocess import FakeProcess

from acta.cli import main
from acta.git.branch import TYPES, get_current_branch
from acta.git.config import get_active_issue
from acta.github.label import TYPE_COLORS

FAKE_REPO = "test-owner/test-repo"
MILESTONE_API = f"repos/{FAKE_REPO}/milestones"
ISSUE_FIELDS = "number,title,labels,milestone"
ISSUE_VIEW_FIELDS = "number,title,labels,milestone,body"


@pytest.fixture
def register_issue_create(fp: FakeProcess) -> Callable[..., None]:
    def _register(
        title: str = "Add login",
        body: str = "",
        stdout: str = f"https://github.com/{FAKE_REPO}/issues/1",
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            [
                "gh",
                "issue",
                "create",
                "--title",
                title,
                "--body",
                body,
                "--repo",
                FAKE_REPO,
                "--label",
                "type: feat",
            ],
            stdout=stdout,
        )

    return _register


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_creates_issue(runner: CliRunner, register_issue_create: Callable[..., None]) -> None:
    register_issue_create()
    result = runner.invoke(main, ["issue", "new", "Add login", "--type", "feat"])
    assert result.exit_code == 0, result.output
    assert result.output == "Issue #1 created.\n"


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_creates_issue_with_body(
    runner: CliRunner, register_issue_create: Callable[..., None]
) -> None:
    register_issue_create(body="Login via SSO.")
    result = runner.invoke(
        main, ["issue", "new", "Add login", "-b", "Login via SSO.", "--type", "feat"]
    )
    assert result.exit_code == 0, result.output
    assert result.output == "Issue #1 created.\n"


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_auto_creates_labels_when_missing(runner: CliRunner, fp: FakeProcess) -> None:
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


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_creates_issue_with_milestone(runner: CliRunner, fp: FakeProcess) -> None:
    fp.register(  # pyright: ignore[reportUnknownMemberType]
        ["gh", "api", f"{MILESTONE_API}/1"],
        stdout=(
            '{"number": 1, "title": "Foundation", "description": "scope: foundation",'
            ' "open_issues": 0, "state": "open"}'
        ),
    )
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
            "Foundation",
        ],
        stdout=f"https://github.com/{FAKE_REPO}/issues/2",
    )
    result = runner.invoke(
        main, ["issue", "new", "Add login", "--type", "feat", "--milestone", "1"]
    )
    assert result.exit_code == 0, result.output
    assert result.output == "Issue #2 created.\n"


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_lists_issues_grouped_by_milestone(runner: CliRunner, fp: FakeProcess) -> None:
    fp.register(  # pyright: ignore[reportUnknownMemberType]
        ["gh", "issue", "list", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS, "--state", "open"],
        stdout=(
            "["
            '{"number": 4, "title": "Auth", "labels": [{"name": "type: feat"}],'
            ' "milestone": {"number": 1, "title": "Foundation"}},'
            '{"number": 3, "title": "Data model", "labels": [{"name": "type: chore"}],'
            ' "milestone": {"number": 1, "title": "Foundation"}},'
            '{"number": 6, "title": "Portfolio", "labels": [{"name": "type: feat"}],'
            ' "milestone": {"number": 2, "title": "Portfolio"}},'
            '{"number": 9, "title": "Backlog item", "labels": [{"name": "type: feat"}],'
            ' "milestone": null}'
            "]"
        ),
    )
    result = runner.invoke(main, ["issue", "list"])
    assert result.exit_code == 0, result.output
    assert result.output == (
        "#1 Foundation\n"
        "  #3  chore  Data model\n"
        "  #4  feat   Auth\n"
        "\n"
        "#2 Portfolio\n"
        "  #6  feat   Portfolio\n"
        "\n"
        "No milestone\n"
        "  #9  feat   Backlog item\n"
    )


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_lists_issues_filtered_is_flat(runner: CliRunner, fp: FakeProcess) -> None:
    fp.register(  # pyright: ignore[reportUnknownMemberType]
        [
            "gh",
            "issue",
            "list",
            "--repo",
            FAKE_REPO,
            "--json",
            ISSUE_FIELDS,
            "--state",
            "open",
            "--milestone",
            "1",
        ],
        stdout=(
            "["
            '{"number": 4, "title": "Auth", "labels": [{"name": "type: feat"}],'
            ' "milestone": {"number": 1, "title": "Foundation"}},'
            '{"number": 3, "title": "Data model", "labels": [{"name": "type: chore"}],'
            ' "milestone": {"number": 1, "title": "Foundation"}}'
            "]"
        ),
    )
    result = runner.invoke(main, ["issue", "list", "--milestone", "1"])
    assert result.exit_code == 0, result.output
    assert result.output == "#3  chore  Data model\n#4  feat   Auth\n"


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_lists_no_issues(runner: CliRunner, fp: FakeProcess) -> None:
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
        ' "milestone": {"number": 1, "title": "Auth System"},'
        ' "body": "## Description\\nLogin form with magic link."}'
    )
    MILESTONE_JSON = (
        '{"number": 1, "title": "Auth System", "description": "scope: auth",'
        ' "open_issues": 1, "state": "open"}'
    )

    @pytest.fixture(autouse=True)
    def _setup(self, fp: FakeProcess) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "1", "--repo", FAKE_REPO, "--json", ISSUE_VIEW_FIELDS],
            stdout=self.ISSUE_JSON,
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", f"{MILESTONE_API}/1"],
            stdout=self.MILESTONE_JSON,
        )

    @pytest.mark.usefixtures("git_repo_with_github_remote")
    def test_creates_branch_and_records_active_issue(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["issue", "start", "1"])
        assert result.exit_code == 0, result.output
        assert result.output == (
            "On branch feat/auth/1-add-login, active issue is #1.\n"
            "\n"
            "## Description\nLogin form with magic link.\n"
        )
        assert get_current_branch() == "feat/auth/1-add-login"
        assert get_active_issue() == 1

    @pytest.mark.usefixtures("git_repo_with_github_remote")
    def test_omits_body_block_when_empty(self, runner: CliRunner, fp: FakeProcess) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "5", "--repo", FAKE_REPO, "--json", ISSUE_VIEW_FIELDS],
            stdout=(
                '{"number": 5, "title": "Terse", "labels": [{"name": "type: feat"}],'
                ' "milestone": {"number": 1, "title": "Auth System"}, "body": ""}'
            ),
        )
        result = runner.invoke(main, ["issue", "start", "5"])
        assert result.exit_code == 0, result.output
        assert result.output == "On branch feat/auth/5-terse, active issue is #5.\n"

    @pytest.mark.usefixtures("git_repo_with_github_remote")
    def test_fails_without_milestone(self, runner: CliRunner, fp: FakeProcess) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "2", "--repo", FAKE_REPO, "--json", ISSUE_VIEW_FIELDS],
            stdout=(
                '{"number": 2, "title": "No milestone",'
                ' "labels": [{"name": "type: feat"}], "milestone": null, "body": ""}'
            ),
        )
        result = runner.invoke(main, ["issue", "start", "2"])
        assert result.exit_code == 1
        assert result.output == (
            "Error: Issue #2 has no milestone — assign it to a milestone first\n"
        )

    @pytest.mark.usefixtures("git_repo_with_github_remote")
    def test_fails_without_scope(self, runner: CliRunner, fp: FakeProcess) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "3", "--repo", FAKE_REPO, "--json", ISSUE_VIEW_FIELDS],
            stdout=(
                '{"number": 3, "title": "No scope issue",'
                ' "labels": [{"name": "type: feat"}],'
                ' "milestone": {"number": 2, "title": "No Scope"}, "body": ""}'
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
        assert result.exit_code == 1
        assert result.output == (
            "Error: Milestone #2 has no scope — its description must start with 'scope: SCOPE'\n"
        )

    @pytest.mark.usefixtures("git_repo_with_github_remote")
    def test_fails_without_type_label(self, runner: CliRunner, fp: FakeProcess) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "4", "--repo", FAKE_REPO, "--json", ISSUE_VIEW_FIELDS],
            stdout=(
                '{"number": 4, "title": "Unlabeled",'
                ' "labels": [],'
                ' "milestone": {"number": 1, "title": "Auth System"}, "body": ""}'
            ),
        )
        result = runner.invoke(main, ["issue", "start", "4"])
        assert result.exit_code == 1
        assert result.output == (
            "Error: Issue #4 has no type label — assign a 'type: TYPE' label on GitHub\n"
        )


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_discards_issue(runner: CliRunner, fp: FakeProcess) -> None:
    fp.register(  # pyright: ignore[reportUnknownMemberType]
        ["gh", "issue", "close", "1", "--reason", "not planned", "--repo", FAKE_REPO],
    )
    result = runner.invoke(main, ["issue", "discard", "1"])
    assert result.exit_code == 0, result.output
    assert result.output == "Issue #1 discarded.\n"
