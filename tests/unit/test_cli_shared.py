import pytest
from click.testing import CliRunner

from acta.cli import main
from acta.cli.shared import strip_comments, strip_type_prefix


@pytest.mark.parametrize("command", ["commit", "branch", "pr", "ship", "release", "board"])
def test_subcommand_help_exits_zero(command: str) -> None:
    # Click's --help raises Exit(0), which subclasses RuntimeError; CLIGroup must not
    # swallow it into a spurious "Error: 0".
    result = CliRunner().invoke(main, [command, "--help"])
    assert result.exit_code == 0, result.output
    assert "Error" not in result.output


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


@pytest.mark.parametrize(
    "title, expected",
    [
        ("add login form", "add login form"),
        ("fix: token TTL", "token TTL"),
        ("fix(auth): token TTL", "token TTL"),
        ("feat!: drop legacy api", "drop legacy api"),
        ("fix(auth)!: token TTL", "token TTL"),
        ("chore: bump deps", "bump deps"),
        ("fixup the reader", "fixup the reader"),
        ("notatype: keep this", "notatype: keep this"),
        ("Fix: keep this", "Fix: keep this"),
    ],
    ids=[
        "no_prefix",
        "bare_type",
        "type_with_scope",
        "breaking_bang",
        "scope_and_bang",
        "another_type",
        "type_as_word_not_prefix",
        "unknown_type_kept",
        "capitalized_kept",
    ],
)
def test_strip_type_prefix(title: str, expected: str) -> None:
    assert strip_type_prefix(title) == expected
