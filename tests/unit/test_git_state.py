from pathlib import Path

import pytest

from acta.git import state


@pytest.fixture(autouse=True)
def state_under_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the state file at a throwaway git dir so each test reads and writes in isolation."""

    def fake_git(*args: str, capture: bool = False, quiet: bool = False) -> str:
        return str(tmp_path)

    monkeypatch.setattr(state, "git", fake_git)


def test_records_and_reads_back_issue_and_pr() -> None:
    state.set_branch_issue("feat/a", 7)
    state.set_branch_pr("feat/a", 34)
    assert (state.get_branch_issue("feat/a"), state.get_branch_pr("feat/a")) == (7, 34)


def test_branch_without_a_record_reads_as_none() -> None:
    assert (state.get_branch_issue("feat/a"), state.get_branch_pr("feat/a")) == (None, None)


@pytest.fixture
def two_recorded_branches() -> None:
    state.set_branch_issue("feat/a", 7)
    state.set_branch_issue("feat/b", 8)


@pytest.mark.usefixtures("two_recorded_branches")
@pytest.mark.parametrize(
    ("cleared", "expected"),
    [
        pytest.param("feat/a", (None, 8), id="clears-feat-a"),
        pytest.param("feat/b", (7, None), id="clears-feat-b"),
        pytest.param("feat/absent", (7, 8), id="ignores-an-unknown-branch"),
    ],
)
def test_clear_branch(cleared: str, expected: tuple[int | None, int | None]) -> None:
    state.clear_branch(cleared)
    assert (state.get_branch_issue("feat/a"), state.get_branch_issue("feat/b")) == expected
