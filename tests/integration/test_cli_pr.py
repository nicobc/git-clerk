import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import CliRunner
from pytest_subprocess import FakeProcess

from acta.cli import main
from acta.git.branch import branch_exists, get_current_branch, switch_main, switch_new_branch
from acta.git.commit import add_all
from acta.git.commit import commit as git_commit
from acta.git.config import get_active_issue, set_active_issue

FAKE_REPO = "test-owner/test-repo"
MILESTONE_API = f"repos/{FAKE_REPO}/milestones"
ISSUE_FIELDS = "number,title,labels,milestone,body"
PR_URL = f"https://github.com/{FAKE_REPO}/pull/1"

# Output of a successful `acta pr`: the opened-PR line, the watch header, the one
# (passing) check, and the all-clear.
PR_SUCCESS_OUTPUT = (
    f"Opened PR #1 at {PR_URL}\nNow watching checks...\n✓ test\nAll checks passed.\n"
)

ROLLUP_CMD = ["gh", "pr", "view", "1", "--repo", FAKE_REPO, "--json", "statusCheckRollup"]
_JOB_URL = f"https://github.com/{FAKE_REPO}/actions/runs/9/job/7"
ROLLUP_PASS = (
    '{"statusCheckRollup": [{"__typename": "CheckRun", "name": "test",'
    ' "status": "COMPLETED", "conclusion": "SUCCESS", "detailsUrl": "' + _JOB_URL + '"}]}'
)
ROLLUP_FAIL = (
    '{"statusCheckRollup": [{"__typename": "CheckRun", "name": "test",'
    ' "status": "COMPLETED", "conclusion": "FAILURE", "detailsUrl": "' + _JOB_URL + '"}]}'
)
ROLLUP_NONE = '{"statusCheckRollup": []}'
JOB_LOG_CMD = ["gh", "run", "view", "--job", "7", "--log-failed", "--repo", FAKE_REPO]


def _noop_sleep(_seconds: float) -> None:
    pass


class TestPr:
    @pytest.fixture
    def register_pr_create(self, fp: FakeProcess) -> Callable[..., None]:
        def _register(title: str = "feat(my-scope): add tests", body: str = "") -> None:
            fp.register(  # pyright: ignore[reportUnknownMemberType]
                [
                    "gh",
                    "pr",
                    "create",
                    "--base",
                    "main",
                    "--title",
                    title,
                    "--body",
                    body,
                    "--repo",
                    FAKE_REPO,
                ],
                stdout=PR_URL,
            )

        return _register

    @pytest.fixture(autouse=True)
    def _setup(self, git_repo_with_github_remote: Path, fp: FakeProcess) -> None:
        switch_new_branch("feat/my-scope")
        (git_repo_with_github_remote / "file.txt").write_text("hello")
        add_all()
        git_commit("feat(my-scope): add something")
        # acta pr watches after creating: _await_checks polls once, then the loop
        # polls once more to read the terminal state.
        fp.register(ROLLUP_CMD, stdout=ROLLUP_PASS, occurrences=2)  # pyright: ignore[reportUnknownMemberType]

    def test_pushes_branch_and_creates_pr(
        self, runner: CliRunner, register_pr_create: Callable[..., None]
    ) -> None:
        register_pr_create()
        result = runner.invoke(main, ["pr", "add tests"])
        assert result.exit_code == 0, result.output
        assert result.output == PR_SUCCESS_OUTPUT

    def test_body_flag_passes_body(
        self, runner: CliRunner, register_pr_create: Callable[..., None]
    ) -> None:
        register_pr_create(body="Adds coverage.")
        result = runner.invoke(main, ["pr", "-b", "Adds coverage.", "add tests"])
        assert result.exit_code == 0, result.output
        assert result.output == PR_SUCCESS_OUTPUT

    def test_body_and_edit_are_mutually_exclusive(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["pr", "-b", "x", "-e", "add tests"])
        assert result.exit_code == 2
        assert "mutually exclusive" in result.output

    def test_breaking_appends_bang_to_title(
        self, runner: CliRunner, register_pr_create: Callable[..., None]
    ) -> None:
        register_pr_create(title="feat(my-scope)!: add tests")
        result = runner.invoke(main, ["pr", "--breaking", "add tests"])
        assert result.exit_code == 0, result.output
        assert result.output == PR_SUCCESS_OUTPUT


class TestShip:
    @pytest.fixture(autouse=True)
    def _on_feature_branch(self, git_repo_with_github_remote: Path, fp: FakeProcess) -> None:
        switch_new_branch("feat/my-scope")
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "view", "feat/my-scope", "--repo", FAKE_REPO, "--json", "number,title"],
            stdout='{"number": 1, "title": "feat(my-scope): add something"}',
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "merge", "1", "--squash", "--delete-branch", "--repo", FAKE_REPO],
        )

    @pytest.fixture
    def _checks_pass(self, fp: FakeProcess) -> None:
        fp.register(ROLLUP_CMD, stdout=ROLLUP_PASS)  # pyright: ignore[reportUnknownMemberType]

    @pytest.fixture
    def _on_main(self) -> None:
        switch_main()

    @pytest.mark.usefixtures("_checks_pass")
    def test_merges_pr_and_returns_to_main(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 0, result.output
        assert get_current_branch() == "main"
        assert not branch_exists("feat/my-scope")

    @pytest.mark.usefixtures("_checks_pass")
    def test_switches_to_update_branch_after_ship(
        self, git_repo_with_github_remote: Path, runner: CliRunner
    ) -> None:
        subprocess.run(
            ["git", "branch", "feat/other", "origin/main"],
            cwd=git_repo_with_github_remote,
            check=True,
        )
        result = runner.invoke(main, ["ship", "-y", "--update", "feat/other"])
        assert result.exit_code == 0, result.output
        assert get_current_branch() == "feat/other"

    @pytest.mark.usefixtures("_checks_pass")
    def test_prunes_stale_tracking_refs_on_ship(
        self, git_repo_with_github_remote: Path, runner: CliRunner
    ) -> None:
        ref = "refs/remotes/origin/chore/old"
        subprocess.run(
            ["git", "update-ref", ref, "HEAD"], cwd=git_repo_with_github_remote, check=True
        )
        exists = ["git", "show-ref", "--verify", "--quiet", ref]
        assert subprocess.run(exists, cwd=git_repo_with_github_remote).returncode == 0
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 0, result.output
        assert subprocess.run(exists, cwd=git_repo_with_github_remote).returncode != 0

    def test_ships_when_no_checks_reported(self, runner: CliRunner, fp: FakeProcess) -> None:
        fp.register(ROLLUP_CMD, stdout=ROLLUP_NONE)  # pyright: ignore[reportUnknownMemberType]
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 0, result.output

    def test_fails_if_checks_failing(self, runner: CliRunner, fp: FakeProcess) -> None:
        fp.register(ROLLUP_CMD, stdout=ROLLUP_FAIL)  # pyright: ignore[reportUnknownMemberType]
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 1
        assert "failing or pending checks" in result.output

    @pytest.mark.usefixtures("_on_main")
    def test_fails_when_on_main(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 1
        assert "feature branch" in result.output


class TestShipWithMilestone:
    @pytest.fixture(autouse=True)
    def _setup(self, git_repo_with_github_remote: Path, fp: FakeProcess) -> None:
        switch_new_branch("feat/auth")
        set_active_issue(1)
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "view", "feat/auth", "--repo", FAKE_REPO, "--json", "number,title"],
            stdout='{"number": 1, "title": "feat(auth): add login"}',
        )
        fp.register(ROLLUP_CMD, stdout=ROLLUP_PASS)  # pyright: ignore[reportUnknownMemberType]
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "merge", "1", "--squash", "--delete-branch", "--repo", FAKE_REPO],
        )

    def test_clears_active_issue_on_ship(self, runner: CliRunner, fp: FakeProcess) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "1", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS],
            stdout=(
                '{"number": 1, "title": "Add login", "labels": [{"name": "type: feat"}],'
                ' "milestone": null}'
            ),
        )
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 0, result.output
        assert get_active_issue() is None

    def test_closes_milestone_when_all_issues_done(
        self, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "1", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS],
            stdout=(
                '{"number": 1, "title": "Add login", "labels": [{"name": "type: feat"}],'
                ' "milestone": {"number": 1, "title": "Auth System"}}'
            ),
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", f"{MILESTONE_API}/1"],
            stdout=(
                '{"number": 1, "title": "Auth System", "description": "scope: auth",'
                ' "open_issues": 0, "state": "open"}'
            ),
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", f"{MILESTONE_API}/1", "--method", "PATCH", "-f", "state=closed"],
        )
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 0, result.output
        assert result.output == (
            "Merged PR #1 feat/auth → main\n"
            "Switched to main, pulled origin/main, deleted feat/auth, and pruned stale refs.\n"
            'Milestone #1 "Auth System" completed and closed.\n'
        )

    def test_does_not_close_milestone_with_open_issues(
        self, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "issue", "view", "1", "--repo", FAKE_REPO, "--json", ISSUE_FIELDS],
            stdout=(
                '{"number": 1, "title": "Add login", "labels": [{"name": "type: feat"}],'
                ' "milestone": {"number": 1, "title": "Auth System"}}'
            ),
        )
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "api", f"{MILESTONE_API}/1"],
            stdout=(
                '{"number": 1, "title": "Auth System", "description": "scope: auth",'
                ' "open_issues": 2, "state": "open"}'
            ),
        )
        result = runner.invoke(main, ["ship", "-y"])
        assert result.exit_code == 0, result.output
        assert result.output == (
            "Merged PR #1 feat/auth → main\n"
            "Switched to main, pulled origin/main, deleted feat/auth, and pruned stale refs.\n"
        )


class TestWatch:
    @pytest.fixture(autouse=True)
    def _setup(self, git_repo_with_github_remote: Path, fp: FakeProcess) -> None:
        switch_new_branch("feat/my-scope")
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            ["gh", "pr", "view", "feat/my-scope", "--repo", FAKE_REPO, "--json", "number,title"],
            stdout='{"number": 1, "title": "feat(my-scope): add something"}',
        )

    @pytest.fixture
    def _instant_sleep(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("acta.cli.checks.time.sleep", _noop_sleep)

    @pytest.fixture
    def _short_queue(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("acta.cli.checks._QUEUE_TIMEOUT", 1)
        monkeypatch.setattr("acta.cli.checks._POLL_INTERVAL", 1)
        monkeypatch.setattr("acta.cli.checks.time.sleep", _noop_sleep)

    def test_reports_each_check_and_passes(self, runner: CliRunner, fp: FakeProcess) -> None:
        # One poll to detect checks, one to read their terminal state.
        fp.register(ROLLUP_CMD, stdout=ROLLUP_PASS, occurrences=2)  # pyright: ignore[reportUnknownMemberType]
        result = runner.invoke(main, ["watch"])
        assert result.exit_code == 0, result.output
        assert result.output == "Now watching checks...\n✓ test\nAll checks passed.\n"

    @pytest.mark.usefixtures("_instant_sleep")
    def test_polls_until_checks_appear_then_passes(
        self, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(ROLLUP_CMD, stdout=ROLLUP_NONE)  # pyright: ignore[reportUnknownMemberType]
        fp.register(ROLLUP_CMD, stdout=ROLLUP_PASS, occurrences=2)  # pyright: ignore[reportUnknownMemberType]
        result = runner.invoke(main, ["watch"])
        assert result.exit_code == 0, result.output
        assert result.output == "Now watching checks...\n✓ test\nAll checks passed.\n"

    @pytest.mark.usefixtures("_short_queue")
    def test_returns_without_watching_when_no_checks_appear(
        self, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(ROLLUP_CMD, stdout=ROLLUP_NONE)  # pyright: ignore[reportUnknownMemberType]
        result = runner.invoke(main, ["watch"])
        assert result.exit_code == 0, result.output
        assert result.output == ""

    def test_surfaces_failure_log_and_exits_nonzero(
        self, runner: CliRunner, fp: FakeProcess
    ) -> None:
        fp.register(ROLLUP_CMD, stdout=ROLLUP_FAIL, occurrences=2)  # pyright: ignore[reportUnknownMemberType]
        fp.register(  # pyright: ignore[reportUnknownMemberType]
            JOB_LOG_CMD,
            stdout="##[error]boom\nProcess completed with exit code 1",
        )
        result = runner.invoke(main, ["watch"])
        assert result.exit_code == 1
        assert result.output == (
            "Now watching checks...\n"
            "✗ test\n"
            "##[error]boom\n"
            "Process completed with exit code 1\n"
            "Error: PR #1 checks failed.\n"
        )
