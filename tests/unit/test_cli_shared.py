import pytest
from click.testing import CliRunner

from acta.cli import main
from acta.cli.shared import strip_comments


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
