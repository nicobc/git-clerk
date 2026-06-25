import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner
from pytest_subprocess import FakeProcess

from acta.cli import main
from acta.git.state import set_branch_issue

FAKE_REPO = "test-owner/test-repo"
MILESTONE_API = f"repos/{FAKE_REPO}/milestones"
ISSUE_FIELDS = "number,title,labels,milestone"
ISSUE_VIEW_FIELDS = "number,title,labels,milestone,body"

MILESTONES_JSON = (
    "["
    '{"number": 1, "title": "Foundation", "description": "scope: foundation",'
    ' "open_issues": 3, "closed_issues": 2},'
    '{"number": 2, "title": "Portfolio", "description": "scope: portfolio",'
    ' "open_issues": 2, "closed_issues": 0}'
    "]"
)
FOUNDATION_ISSUES_JSON = (
    "["
    '{"number": 4, "title": "Auth", "labels": [{"name": "type: feat"}],'
    ' "milestone": {"number": 1, "title": "Foundation"}},'
    '{"number": 3, "title": "Data model", "labels": [{"name": "type: chore"}],'
    ' "milestone": {"number": 1, "title": "Foundation"}}'
    "]"
)
EXPANDED_FOUNDATION = (
    "#1  Foundation — 3 issues open, 2 closed\n"
    "  #3  chore  Data model\n"
    "  #4  feat   Auth\n"
    "\n"
    "#2  Portfolio — 2 issues open\n"
)


def _register_foundation(fp: FakeProcess) -> None:
    fp.register(  # pyright: ignore[reportUnknownMemberType]
        ["gh", "api", MILESTONE_API, "-X", "GET", "-f", "state=open"],
        stdout=MILESTONES_JSON,
    )
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
        stdout=FOUNDATION_ISSUES_JSON,
    )


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_board_with_active_issue_focuses_its_milestone(runner: CliRunner, fp: FakeProcess) -> None:
    subprocess.run(["git", "switch", "-c", "feat/foundation"], check=True, capture_output=True)
    set_branch_issue("feat/foundation", 4)
    fp.register(  # pyright: ignore[reportUnknownMemberType]
        ["gh", "issue", "view", "4", "--repo", FAKE_REPO, "--json", ISSUE_VIEW_FIELDS],
        stdout=(
            '{"number": 4, "title": "Auth", "labels": [{"name": "type: feat"}],'
            ' "milestone": {"number": 1, "title": "Foundation"}, "body": "Magic link."}'
        ),
    )
    _register_foundation(fp)
    result = runner.invoke(main, ["board"])
    assert result.exit_code == 0, result.output
    assert result.output == (
        "Current branch: feat/foundation\nActive issue: #4 Auth\n\n" + EXPANDED_FOUNDATION
    )


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_board_without_active_issue_focuses_first_milestone(
    runner: CliRunner, fp: FakeProcess
) -> None:
    _register_foundation(fp)
    result = runner.invoke(main, ["board"])
    assert result.exit_code == 0, result.output
    assert result.output == "Current branch: main\n\n" + EXPANDED_FOUNDATION


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_board_no_milestones(runner: CliRunner, fp: FakeProcess) -> None:
    fp.register(  # pyright: ignore[reportUnknownMemberType]
        ["gh", "api", MILESTONE_API, "-X", "GET", "-f", "state=open"],
        stdout="[]",
    )
    result = runner.invoke(main, ["board"])
    assert result.exit_code == 0, result.output
    assert result.output == "Current branch: main\n\nNo open milestones.\n"


def test_board_lists_working_tree_changes(
    runner: CliRunner, fp: FakeProcess, git_repo_with_github_remote: Path
) -> None:
    (git_repo_with_github_remote / "new.txt").write_text("hi")
    _register_foundation(fp)
    result = runner.invoke(main, ["board"])
    assert result.exit_code == 0, result.output
    assert result.output == (
        "Current branch: main\n\nWorking tree:\n?? new.txt\n\n" + EXPANDED_FOUNDATION
    )


@pytest.mark.usefixtures("git_repo_with_github_remote")
def test_board_lists_unpushed_commits(runner: CliRunner, fp: FakeProcess) -> None:
    subprocess.run(["git", "switch", "-c", "feat/foundation"], check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "feat(foundation): add a"],
        check=True,
        capture_output=True,
    )
    _register_foundation(fp)
    result = runner.invoke(main, ["board"])
    assert result.exit_code == 0, result.output
    assert result.output == (
        "Current branch: feat/foundation\n\nUnpushed commits:\nfeat(foundation): add a\n\n"
        + EXPANDED_FOUNDATION
    )
