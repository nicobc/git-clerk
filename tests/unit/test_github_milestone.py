import pytest

from acta.github.milestone import parse_description


@pytest.mark.parametrize(
    "raw, expected_scope, expected_description",
    [
        ("", "", ""),
        ("scope: auth", "auth", ""),
        ("scope: auth\n\nBuild authentication.", "auth", "Build authentication."),
        ("scope: auth\n\nLine one.\nLine two.", "auth", "Line one.\nLine two."),
        ("No scope prefix here.", "", "No scope prefix here."),
    ],
    ids=[
        "empty",
        "scope_only",
        "scope_and_description",
        "scope_and_multiline_description",
        "no_scope",
    ],
)
def test_parse_description(raw: str, expected_scope: str, expected_description: str) -> None:
    scope, description = parse_description(raw)
    assert scope == expected_scope
    assert description == expected_description
