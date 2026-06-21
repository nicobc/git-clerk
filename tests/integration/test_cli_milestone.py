import pytest
from click.testing import CliRunner
from pytest_subprocess import FakeProcess

from acta.cli import main

FAKE_REPO = "test-owner/test-repo"
MILESTONE_API = f"repos/{FAKE_REPO}/milestones"


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_creates_milestone(runner: CliRunner, fp: FakeProcess) -> None:
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


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_creates_milestone_with_description(runner: CliRunner, fp: FakeProcess) -> None:
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
        main, ["milestone", "new", "Auth System", "-d", "Build authentication.", "--scope", "auth"]
    )
    assert result.exit_code == 0, result.output
    assert result.output == "Milestone #2 created.\n"


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_lists_milestones(runner: CliRunner, fp: FakeProcess) -> None:
    fp.register(  # pyright: ignore[reportUnknownMemberType]
        ["gh", "api", MILESTONE_API, "-X", "GET", "-f", "state=open"],
        stdout=(
            '[{"number": 1, "title": "Auth System", "description": "scope: auth",'
            ' "open_issues": 3, "closed_issues": 1}]'
        ),
    )
    result = runner.invoke(main, ["milestone", "list"])
    assert result.exit_code == 0, result.output
    assert result.output == ("test-repo milestones:\n#1  Auth System — 3 issues open, 1 closed\n")


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_omits_closed_count_when_zero(runner: CliRunner, fp: FakeProcess) -> None:
    fp.register(  # pyright: ignore[reportUnknownMemberType]
        ["gh", "api", MILESTONE_API, "-X", "GET", "-f", "state=open"],
        stdout=(
            '[{"number": 2, "title": "Portfolio", "description": "scope: portfolio",'
            ' "open_issues": 2, "closed_issues": 0}]'
        ),
    )
    result = runner.invoke(main, ["milestone", "list"])
    assert result.exit_code == 0, result.output
    assert result.output == "test-repo milestones:\n#2  Portfolio — 2 issues open\n"


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_lists_no_milestones(runner: CliRunner, fp: FakeProcess) -> None:
    fp.register(  # pyright: ignore[reportUnknownMemberType]
        ["gh", "api", MILESTONE_API, "-X", "GET", "-f", "state=open"],
        stdout="[]",
    )
    result = runner.invoke(main, ["milestone", "list"])
    assert result.exit_code == 0, result.output
    assert result.output == "No open milestones.\n"


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_reopens_milestone(runner: CliRunner, fp: FakeProcess) -> None:
    fp.register(  # pyright: ignore[reportUnknownMemberType]
        ["gh", "api", f"{MILESTONE_API}/1", "--method", "PATCH", "-f", "state=open"],
    )
    result = runner.invoke(main, ["milestone", "reopen", "1"])
    assert result.exit_code == 0, result.output
    assert result.output == "Milestone #1 reopened.\n"
