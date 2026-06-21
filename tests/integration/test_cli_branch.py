import pytest
from click.testing import CliRunner

from acta.cli import main
from acta.git.branch import get_current_branch, switch_main, switch_new_branch


@pytest.mark.usefixtures("git_repo")
def test_creates_branch_from_origin_main(runner: CliRunner) -> None:
    result = runner.invoke(main, ["branch", "feat/my-scope"])
    assert result.exit_code == 0, result.output
    assert get_current_branch() == "feat/my-scope"


@pytest.mark.usefixtures("git_repo")
def test_rejects_invalid_type(runner: CliRunner) -> None:
    result = runner.invoke(main, ["branch", "notatype/scope"])
    assert result.exit_code == 1
    assert "'notatype' is not a conventional commit type" in result.output


@pytest.mark.usefixtures("git_repo")
def test_rejects_existing_branch(runner: CliRunner) -> None:
    switch_new_branch("feat/my-scope")
    switch_main()
    result = runner.invoke(main, ["branch", "feat/my-scope"])
    assert result.exit_code == 128
    assert get_current_branch() == "main"
