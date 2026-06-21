import pytest

from acta.github import parse_repo_from_url


@pytest.mark.parametrize(
    "input_url, expected",
    [
        ("https://github.com/owner/repo.git", "owner/repo"),
        ("https://github.com/owner/repo", "owner/repo"),
        ("git@github.com:owner/repo.git", "owner/repo"),
        ("git@github.com:owner/repo", "owner/repo"),
        ("ssh://git@github.com/owner/repo.git", "owner/repo"),
    ],
    ids=[
        "https_with_git",
        "https_without_git",
        "ssh_scp_with_git",
        "ssh_scp_without_git",
        "ssh_url",
    ],
)
def test_parse_repo_from_url(input_url: str, expected: str) -> None:
    assert parse_repo_from_url(input_url) == expected


@pytest.mark.parametrize(
    "input_url",
    ["https://github.com/nodepth", "not-a-url"],
    ids=["missing_owner", "not_a_url"],
)
def test_parse_repo_from_url_invalid(input_url: str) -> None:
    with pytest.raises(ValueError):
        parse_repo_from_url(input_url)
