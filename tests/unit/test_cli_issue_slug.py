import pytest

from acta.cli.issue import slugify_title


@pytest.mark.parametrize(
    "title, expected",
    [
        ("Add login form", "add-login-form"),
        ("Fix token expiry!", "fix-token-expiry"),
        ("  Trim  whitespace  ", "trim-whitespace"),
        ("Already-hyphenated", "already-hyphenated"),
        ("Symbols: @#$%", "symbols"),
        ("café ünïcode", "caf-n-code"),
        ("!!!", ""),
        ("", ""),
    ],
)
def test_slugify_title(title: str, expected: str) -> None:
    assert slugify_title(title) == expected


def test_slugify_title_truncates_without_trailing_hyphen() -> None:
    slug = slugify_title("word " * 20)
    assert len(slug) <= 40
    assert not slug.endswith("-")
