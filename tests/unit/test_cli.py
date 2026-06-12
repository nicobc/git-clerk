import pytest

from gitclerk.cli.shared import strip_comments


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("", ""),
        ("# comment", ""),
        ("# line one\n# line two", ""),
        ("some body", "some body"),
        ("# comment\n\nsome body", "some body"),
        ("some body\n\n# comment", "some body"),
        (
            "first paragraph\n\n# comment\n\nsecond paragraph",
            "first paragraph\n\nsecond paragraph",
        ),
        ("\n\nsome body\n\n", "some body"),
        ("a line with # hash inside", "a line with # hash inside"),
    ],
    ids=[
        "empty",
        "single_comment",
        "only_comments",
        "no_comments",
        "leading_comment",
        "trailing_comment",
        "comment_between_paragraphs",
        "strips_surrounding_whitespace",
        "inline_hash_preserved",
    ],
)
def test_strip_comments(raw: str, expected: str) -> None:
    assert strip_comments(raw) == expected
