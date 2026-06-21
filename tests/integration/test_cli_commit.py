import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from acta.cli import main
from acta.git.branch import switch_new_branch


def _commit_subject() -> str:
    return subprocess.run(
        ["git", "log", "--format=%s", "-1"],
        capture_output=True,
        text=True,
    ).stdout.strip()


class TestCommit:
    @pytest.fixture(autouse=True)
    def _on_feature_branch(self, git_repo: Path) -> None:
        switch_new_branch("feat/my-scope")

    @pytest.fixture(autouse=True)
    def _add_file(self, git_repo: Path) -> None:
        (git_repo / "file.txt").write_text("hello")

    @pytest.fixture
    def _stage_file(self, git_repo: Path) -> None:
        subprocess.run(["git", "add", "file.txt"], cwd=git_repo, check=True)

    @pytest.mark.usefixtures("_stage_file")
    def test_formats_message_from_branch_name(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["commit", "add test file"])
        assert result.exit_code == 0, result.output
        assert _commit_subject() == "feat(my-scope): add test file"

    @pytest.mark.usefixtures("_stage_file")
    def test_body_flag_adds_body(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["commit", "-b", "Extra context.", "add test file"])
        assert result.exit_code == 0, result.output
        body = subprocess.run(
            ["git", "log", "--format=%b", "-1"], capture_output=True, text=True
        ).stdout.strip()
        assert body == "Extra context."

    @pytest.mark.usefixtures("_stage_file")
    def test_body_and_edit_are_mutually_exclusive(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["commit", "-b", "x", "-e", "add test file"])
        assert result.exit_code == 2
        assert "mutually exclusive" in result.output

    def test_stage_all_long_form(self, git_repo: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["commit", "--stage-all", "add test file"])
        assert result.exit_code == 0, result.output

    def test_stage_all_flag(self, git_repo: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["commit", "-A", "add test file"])
        assert result.exit_code == 0, result.output
        committed = (
            subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "-r", "--name-only", "HEAD"],
                capture_output=True,
                text=True,
                cwd=git_repo,
            )
            .stdout.strip()
            .splitlines()
        )
        assert "file.txt" in committed

    @pytest.mark.usefixtures("_stage_file")
    def test_type_override(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["commit", "-t", "fix", "fix bug"])
        assert result.exit_code == 0, result.output
        assert _commit_subject() == "fix(my-scope): fix bug"

    @pytest.mark.usefixtures("_stage_file")
    def test_scope_override(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["commit", "-s", "other", "cross-cutting change"])
        assert result.exit_code == 0, result.output
        assert _commit_subject() == "feat(other): cross-cutting change"

    def test_push_flag_pushes_to_origin(self, git_repo: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["commit", "-AP", "add test file"])
        assert result.exit_code == 0, result.output
        assert "gh pr edit" in result.output
        local_head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=git_repo, capture_output=True, text=True
        ).stdout.strip()
        remote_head = subprocess.run(
            ["git", "rev-parse", "origin/feat/my-scope"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert remote_head == local_head
