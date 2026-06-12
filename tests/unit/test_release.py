from datetime import date

import pytest

from gitclerk.git.tag import CALVER, SEMVER, Scheme, detect_scheme, next_calver, next_semver


@pytest.mark.parametrize(
    "input_tags, expected",
    [
        ([], None),
        (["v2026.06.1"], CALVER),
        (["v1.0.0"], SEMVER),
        (["latest", "v1"], None),
    ],
    ids=["empty", "calver_only", "semver_only", "non_version_tags"],
)
def test_detect_scheme(input_tags: list[str], expected: Scheme | None) -> None:
    assert detect_scheme(input_tags) == expected


def test_detect_scheme_mixed_raises() -> None:
    with pytest.raises(ValueError, match="mixed"):
        detect_scheme(["v2026.06.1", "v1.0.0"])


@pytest.mark.parametrize(
    "input_tags, expected",
    [
        ([], "v2026.06.1"),
        (["v2026.06.1"], "v2026.06.2"),
        (["v2026.06.1", "v2026.06.2", "v2026.06.3"], "v2026.06.4"),
        (["v2026.05.1", "v2026.05.2"], "v2026.06.1"),
        (["v2026.05.10", "v2026.06.1"], "v2026.06.2"),
    ],
    ids=["no_tags", "one_tag", "three_tags", "previous_month_resets", "mixed_months"],
)
def test_next_calver(today: date, input_tags: list[str], expected: str) -> None:
    assert next_calver(input_tags, today) == expected


@pytest.mark.parametrize(
    "input_tags, input_bump, expected",
    [
        ([], "patch", "v0.1.0"),
        (["v0.1.0"], "patch", "v0.1.1"),
        (["v0.1.0"], "minor", "v0.2.0"),
        (["v0.1.0"], "major", "v1.0.0"),
        (["v0.1.0", "v0.1.5", "v0.2.0"], "patch", "v0.2.1"),
        (["v2026.06.1", "v1.0.0"], "patch", "v1.0.1"),
    ],
    ids=["no_tags", "patch", "minor", "major", "picks_highest", "ignores_calver"],
)
def test_next_semver(input_tags: list[str], input_bump: str, expected: str) -> None:
    assert next_semver(input_tags, input_bump) == expected
