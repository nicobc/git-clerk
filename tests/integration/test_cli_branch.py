import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from acta.cli import main
from acta.git.branch import get_current_branch, switch_main, switch_new_branch


def _tracking_ref_exists(repo: Path, ref: str) -> bool:
    return subprocess.run(["git", "show-ref", "--verify", "--quiet", ref], cwd=repo).returncode == 0


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


def test_prunes_stale_tracking_refs(git_repo: Path, runner: CliRunner) -> None:
    # A leftover tracking ref whose remote branch is gone (forged here) would otherwise
    # D/F-conflict with a later same-prefix branch like chore/foundation/N-topic.
    ref = "refs/remotes/origin/chore/foundation"
    subprocess.run(["git", "update-ref", ref, "HEAD"], cwd=git_repo, check=True)
    assert _tracking_ref_exists(git_repo, ref)
    result = runner.invoke(main, ["branch", "chore/other"])
    assert result.exit_code == 0, result.output
    assert not _tracking_ref_exists(git_repo, ref)
