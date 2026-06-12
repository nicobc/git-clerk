import pytest

from gitclerk.git.branch import parse


@pytest.mark.parametrize(
    "input_branch, expected",
    [
        ("feat/login", ("feat", "login")),
        ("fix/user-auth", ("fix", "user-auth")),
        ("refactor/db-layer", ("refactor", "db-layer")),
        ("chore/cleanup", ("chore", "cleanup")),
        ("docs/api-guide", ("docs", "api-guide")),
        ("feat/MY_FEATURE", ("feat", "MY_FEATURE")),
        ("fix/User_Auth", ("fix", "User_Auth")),
    ],
    ids=["feat", "fix", "refactor", "chore", "docs", "uppercase", "mixed_case_underscore"],
)
def test_parse(input_branch: str, expected: tuple[str, str]) -> None:
    assert parse(input_branch) == expected


@pytest.mark.parametrize(
    "input_branch",
    ["feature", "feat/login/extra", "invalid/scope", "", "feat/", "feat/-bad"],
    ids=[
        "no_slash",
        "multiple_slashes",
        "invalid_type",
        "empty",
        "empty_scope",
        "scope_starts_with_hyphen",
    ],
)
def test_parse_invalid(input_branch: str) -> None:
    with pytest.raises(ValueError):
        parse(input_branch)
