import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from git_clerk.cli import main


def _current_branch(cwd: Path) -> str:
    return subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        cwd=cwd,
    ).stdout.strip()


def _commit_subject(cwd: Path) -> str:
    return subprocess.run(
        ["git", "log", "--format=%s", "-1"],
        capture_output=True,
        text=True,
        cwd=cwd,
    ).stdout.strip()


def _tag_list(cwd: Path) -> list[str]:
    out = subprocess.run(
        ["git", "tag", "--list"],
        capture_output=True,
        text=True,
        cwd=cwd,
    ).stdout.strip()
    return out.splitlines() if out else []


class TestBranch:
    def test_creates_branch_from_origin_main(self, git_repo: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["branch", "feat/my-scope"])
        assert result.exit_code == 0
        assert _current_branch(git_repo) == "feat/my-scope"

    def test_invalid_type_exits_nonzero(self, git_repo: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["branch", "notatype/scope"])
        assert result.exit_code != 0

    def test_existing_branch_exits_nonzero(self, git_repo: Path, runner: CliRunner) -> None:
        subprocess.run(
            ["git", "switch", "-c", "feat/my-scope", "origin/main"], cwd=git_repo, check=True
        )
        subprocess.run(["git", "switch", "main"], cwd=git_repo, check=True)
        result = runner.invoke(main, ["branch", "feat/my-scope"])
        assert result.exit_code != 0


class TestCommit:
    @pytest.fixture(autouse=True)
    def on_feature_branch(self, git_repo: Path) -> None:
        subprocess.run(
            ["git", "switch", "-c", "feat/my-scope", "origin/main"], cwd=git_repo, check=True
        )

    def test_formats_message_from_branch_name(self, git_repo: Path, runner: CliRunner) -> None:
        (git_repo / "file.txt").write_text("hello")
        subprocess.run(["git", "add", "file.txt"], cwd=git_repo, check=True)
        result = runner.invoke(main, ["commit", "add test file"])
        assert result.exit_code == 0
        assert _commit_subject(git_repo) == "feat(my-scope): add test file"

    def test_stage_all_flag(self, git_repo: Path, runner: CliRunner) -> None:
        (git_repo / "file.txt").write_text("hello")
        # deliberately skip `git add` — the -A flag must stage the file itself
        result = runner.invoke(main, ["commit", "-A", "add test file"])
        assert result.exit_code == 0
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

    def test_type_override(self, git_repo: Path, runner: CliRunner) -> None:
        (git_repo / "file.txt").write_text("hello")
        subprocess.run(["git", "add", "file.txt"], cwd=git_repo, check=True)
        result = runner.invoke(main, ["commit", "-t", "fix", "fix bug"])
        assert result.exit_code == 0
        assert _commit_subject(git_repo) == "fix(my-scope): fix bug"

    def test_scope_override(self, git_repo: Path, runner: CliRunner) -> None:
        (git_repo / "file.txt").write_text("hello")
        subprocess.run(["git", "add", "file.txt"], cwd=git_repo, check=True)
        result = runner.invoke(main, ["commit", "-s", "other", "cross-cutting change"])
        assert result.exit_code == 0
        assert _commit_subject(git_repo) == "feat(other): cross-cutting change"


class TestRelease:
    def test_calver_creates_tag(self, git_repo: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["release", "--calver", "-y"])
        assert result.exit_code == 0
        assert len(_tag_list(git_repo)) == 1

    def test_semver_creates_initial_tag(self, git_repo: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["release", "--semver", "--bump", "patch", "-y"])
        assert result.exit_code == 0
        assert "v0.1.0" in _tag_list(git_repo)

    def test_semver_increments_existing_tag(self, git_repo: Path, runner: CliRunner) -> None:
        runner.invoke(main, ["release", "--semver", "--bump", "patch", "-y"])
        result = runner.invoke(main, ["release", "--semver", "--bump", "minor", "-y"])
        assert result.exit_code == 0
        assert "v0.2.0" in _tag_list(git_repo)

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
