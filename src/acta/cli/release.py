from datetime import date

import click

from acta.git.tag import (
    CALVER,
    SEMVER,
    Scheme,
    compute_next_calver,
    create_tag,
    detect_scheme,
    fetch_tags,
    list_tags,
    next_release_tag,
)


@click.command()
@click.option(
    "--scheme",
    "scheme",
    type=click.Choice([CALVER, SEMVER], case_sensitive=False),
    default=None,
    help="Versioning scheme: calver (vYYYY.MM.N) or semver (vMAJOR.MINOR.PATCH).",
)
@click.option(
    "--stable", is_flag=True, help="Promote a 0.x project to v1.0.0 (SemVer only, one-time)."
)
@click.option("-y", "--yes", "confirmed", is_flag=True, help="Skip confirmation prompt.")
def release(scheme: Scheme | None, stable: bool, confirmed: bool) -> None:
    """Tag origin/main and push the tag.

    The SemVer bump is derived from the conventional-commit subjects since the last
    tag: a `feat` (or, once stable, a `!` breaking change) bumps minor (major when
    stable); anything else, patch. While still 0.x a breaking change is capped at
    minor — pass --stable for the deliberate one-time jump to v1.0.0.
    """
    fetch_tags()
    existing_tags = list_tags()
    if not scheme:
        try:
            scheme = detect_scheme(existing_tags)
        except ValueError as error:
            raise click.ClickException(str(error))
    if not scheme:
        click.echo("No existing tags found. Choose a versioning scheme:")
        click.echo(
            f"  {CALVER}   vYYYY.MM.N         — calendar versioning, counter resets each month"
        )
        click.echo(f"  {SEMVER}   vMAJOR.MINOR.PATCH — semantic versioning")
        scheme_input = click.prompt(
            "Scheme", type=click.Choice([CALVER, SEMVER], case_sensitive=False), show_choices=False
        )
        scheme = CALVER if scheme_input == CALVER else SEMVER
    if stable and scheme == CALVER:
        raise click.ClickException("--stable applies to SemVer only")
    if scheme == CALVER:
        tag = compute_next_calver(existing_tags, date.today())
    else:
        try:
            tag = next_release_tag(existing_tags, stable)
        except ValueError as error:
            raise click.ClickException(str(error))
    if not confirmed:
        click.confirm(f"Tag and push {tag}", abort=True)
    create_tag(tag)
    click.echo(f"Tagged and pushed {tag}")
