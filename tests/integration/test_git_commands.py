import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from gitclerk.cli import main
from gitclerk.git.branch import current_branch, switch_main, switch_new_branch
from gitclerk.git.tag import tags


def _commit_subject() -> str:
    return subprocess.run(
        ["git", "log", "--format=%s", "-1"],
        capture_output=True,
        text=True,
    ).stdout.strip()


class TestBranch:
    def test_creates_branch_from_origin_main(self, git_repo: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["branch", "feat/my-scope"])
        assert result.exit_code == 0, result.output
        assert current_branch() == "feat/my-scope"

    def test_invalid_type_exits_nonzero(self, git_repo: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["branch", "notatype/scope"])
        assert result.exit_code != 0

    def test_existing_branch_exits_nonzero(self, git_repo: Path, runner: CliRunner) -> None:
        switch_new_branch("feat/my-scope")
        switch_main()
        result = runner.invoke(main, ["branch", "feat/my-scope"])
        assert result.exit_code != 0


class TestCommit:
    @pytest.fixture(autouse=True)
    def _on_feature_branch(self, git_repo: Path) -> None:
        switch_new_branch("feat/my-scope")

    @pytest.fixture(autouse=True)
    def _add_file_to_repo(self, git_repo: Path) -> None:
        (git_repo / "file.txt").write_text("hello")

    @pytest.fixture
    def _stage_file(self, git_repo: Path) -> None:
        subprocess.run(["git", "add", "file.txt"], cwd=git_repo, check=True)

    @pytest.mark.usefixtures("_stage_file")
    def test_formats_message_from_branch_name(self, git_repo: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["commit", "add test file"])
        assert result.exit_code == 0, result.output
        assert _commit_subject() == "feat(my-scope): add test file"

    def test_stage_all_flag(self, git_repo: Path, runner: CliRunner) -> None:
        # deliberately skip `git add` — the -A flag must stage the file itself
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
    def test_type_override(self, git_repo: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["commit", "-t", "fix", "fix bug"])
        assert result.exit_code == 0, result.output
        assert _commit_subject() == "fix(my-scope): fix bug"

    @pytest.mark.usefixtures("_stage_file")
    def test_scope_override(self, git_repo: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["commit", "-s", "other", "cross-cutting change"])
        assert result.exit_code == 0, result.output
        assert _commit_subject() == "feat(other): cross-cutting change"


class TestRelease:
    def test_calver_creates_tag(self, git_repo: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["release", "--calver", "-y"])
        assert result.exit_code == 0, result.output
        assert len(tags(pattern="*")) == 1

    def test_semver_creates_initial_tag(self, git_repo: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["release", "--semver", "--bump", "patch", "-y"])
        assert result.exit_code == 0, result.output
        assert "v0.1.0" in tags()

    def test_semver_increments_existing_tag(self, git_repo: Path, runner: CliRunner) -> None:
        runner.invoke(main, ["release", "--semver", "--bump", "patch", "-y"])
        result = runner.invoke(main, ["release", "--semver", "--bump", "minor", "-y"])
        assert result.exit_code == 0, result.output
        assert "v0.2.0" in tags()

    def test_tag_is_pushed_to_remote(
        self, git_repo: Path, bare_remote: Path, runner: CliRunner
    ) -> None:
        runner.invoke(main, ["release", "--semver", "--bump", "patch", "-y"])
        remote_tags = (
            subprocess.run(
                ["git", "tag", "--list"],
                capture_output=True,
                text=True,
                cwd=bare_remote,
            )
            .stdout.strip()
            .splitlines()
        )
        assert "v0.1.0" in remote_tags
