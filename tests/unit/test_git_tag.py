from datetime import date

import pytest

from acta.git.tag import (
    CALVER,
    SEMVER,
    Scheme,
    compute_next_calver,
    compute_next_semver,
    derive_bump,
    detect_scheme,
    latest_semver_tag,
    next_release_tag,
)


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
def test_compute_next_calver(today: date, input_tags: list[str], expected: str) -> None:
    assert compute_next_calver(input_tags, today) == expected


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
def test_compute_next_semver(input_tags: list[str], input_bump: str, expected: str) -> None:
    assert compute_next_semver(input_tags, input_bump) == expected


@pytest.mark.parametrize(
    "input_tags, expected",
    [
        ([], None),
        (["v0.1.0"], "v0.1.0"),
        (["v0.1.0", "v0.1.5", "v0.2.0"], "v0.2.0"),
        (["v0.2.0", "v0.10.0"], "v0.10.0"),
        (["v2026.06.1", "v1.0.0"], "v1.0.0"),
    ],
    ids=["none", "one", "picks_highest", "numeric_order", "ignores_calver"],
)
def test_latest_semver_tag(input_tags: list[str], expected: str | None) -> None:
    assert latest_semver_tag(input_tags) == expected


@pytest.mark.parametrize(
    "subjects, current_major, expected",
    [
        ([], 0, "patch"),
        (["fix(app): a bug"], 0, "patch"),
        (["feat(app): a thing"], 0, "minor"),
        (["feat(app)!: breaking"], 0, "minor"),  # breaking capped at minor pre-1.0
        (["refactor(app)!: breaking"], 0, "minor"),
        (["chore: x", "feat: y"], 0, "minor"),
        (["fix(app): a bug"], 1, "patch"),
        (["feat(app): a thing"], 1, "minor"),
        (["feat(app)!: breaking"], 1, "major"),  # breaking drives major once stable
        (["refactor(app)!: breaking"], 1, "major"),
        (["chore: x", "feat!: y"], 1, "major"),
        (["not a conventional subject"], 1, "patch"),
    ],
    ids=[
        "empty_patch",
        "fix_patch",
        "feat_minor",
        "breaking_capped_pre_1_0",
        "any_breaking_capped_pre_1_0",
        "feat_among_others_minor",
        "fix_patch_stable",
        "feat_minor_stable",
        "breaking_major_stable",
        "any_breaking_major_stable",
        "breaking_among_others_major",
        "non_conventional_patch",
    ],
)
def test_derive_bump(subjects: list[str], current_major: int, expected: str) -> None:
    assert derive_bump(subjects, current_major) == expected


def test_next_release_tag_stable_promotes_0x_to_v1() -> None:
    assert next_release_tag(["v0.7.0"], stable=True) == "v1.0.0"


def test_next_release_tag_stable_rejects_when_already_stable() -> None:
    with pytest.raises(ValueError, match="already stable"):
        next_release_tag(["v1.2.3"], stable=True)
