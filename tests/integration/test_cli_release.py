import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from acta.cli import main
from acta.git.tag import list_tags


def _commit_and_push(git_repo: Path, subject: str) -> None:
    subprocess.run(["git", "commit", "--allow-empty", "-m", subject], cwd=git_repo, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=git_repo, check=True)


@pytest.mark.usefixtures("git_repo")
def test_calver_creates_tag(runner: CliRunner) -> None:
    result = runner.invoke(main, ["release", "--scheme", "calver", "-y"])
    assert result.exit_code == 0, result.output
    assert len(list_tags(pattern="*")) == 1


@pytest.mark.usefixtures("git_repo")
def test_semver_first_release_is_v0_1_0(runner: CliRunner) -> None:
    result = runner.invoke(main, ["release", "--scheme", "semver", "-y"])
    assert result.exit_code == 0, result.output
    assert "v0.1.0" in list_tags()


def test_semver_derives_patch_without_a_feat(git_repo: Path, runner: CliRunner) -> None:
    runner.invoke(main, ["release", "--scheme", "semver", "-y"])  # v0.1.0
    _commit_and_push(git_repo, "fix(app): a bug")
    result = runner.invoke(main, ["release", "-y"])
    assert result.exit_code == 0, result.output
    assert "v0.1.1" in list_tags()


def test_semver_derives_minor_for_a_feat(git_repo: Path, runner: CliRunner) -> None:
    runner.invoke(main, ["release", "--scheme", "semver", "-y"])  # v0.1.0
    _commit_and_push(git_repo, "feat(app): a feature")
    result = runner.invoke(main, ["release", "-y"])
    assert result.exit_code == 0, result.output
    assert "v0.2.0" in list_tags()


def test_semver_caps_breaking_at_minor_pre_1_0(git_repo: Path, runner: CliRunner) -> None:
    runner.invoke(main, ["release", "--scheme", "semver", "-y"])  # v0.1.0
    _commit_and_push(git_repo, "feat(app)!: breaking change")
    result = runner.invoke(main, ["release", "-y"])
    assert result.exit_code == 0, result.output
    assert "v0.2.0" in list_tags()  # capped — not v1.0.0


def test_stable_promotes_to_v1(git_repo: Path, runner: CliRunner) -> None:
    runner.invoke(main, ["release", "--scheme", "semver", "-y"])  # v0.1.0
    result = runner.invoke(main, ["release", "--stable", "-y"])
    assert result.exit_code == 0, result.output
    assert "v1.0.0" in list_tags()


def test_breaking_drives_major_once_stable(git_repo: Path, runner: CliRunner) -> None:
    runner.invoke(main, ["release", "--scheme", "semver", "-y"])  # v0.1.0
    runner.invoke(main, ["release", "--stable", "-y"])  # v1.0.0
    _commit_and_push(git_repo, "feat(app)!: breaking change")
    result = runner.invoke(main, ["release", "-y"])
    assert result.exit_code == 0, result.output
    assert "v2.0.0" in list_tags()


def test_stable_rejected_when_already_stable(git_repo: Path, runner: CliRunner) -> None:
    runner.invoke(main, ["release", "--scheme", "semver", "-y"])  # v0.1.0
    runner.invoke(main, ["release", "--stable", "-y"])  # v1.0.0
    result = runner.invoke(main, ["release", "--stable", "-y"])
    assert result.exit_code == 1
    assert "already stable" in result.output


@pytest.mark.usefixtures("git_repo")
def test_tag_is_pushed_to_remote(bare_remote: Path, runner: CliRunner) -> None:
    runner.invoke(main, ["release", "--scheme", "semver", "-y"])
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
