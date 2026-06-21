import pytest

from acta.git.branch import parse


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
        ("feat/login/12-add-form", ("feat", "login")),
        ("fix/user-auth/topic", ("fix", "user-auth")),
    ],
    ids=[
        "feat",
        "fix",
        "refactor",
        "chore",
        "docs",
        "uppercase",
        "mixed_case_underscore",
        "topic_segment",
        "topic_segment_named",
    ],
)
def test_parse(input_branch: str, expected: tuple[str, str]) -> None:
    assert parse(input_branch) == expected


@pytest.mark.parametrize(
    "input_branch",
    ["feature", "invalid/scope", "", "feat/", "feat/-bad", "feat/login/"],
    ids=[
        "no_slash",
        "invalid_type",
        "empty",
        "empty_scope",
        "scope_starts_with_hyphen",
        "empty_topic",
    ],
)
def test_parse_invalid(input_branch: str) -> None:
    with pytest.raises(ValueError):
        parse(input_branch)
