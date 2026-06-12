from datetime import date

import click

from gitclerk.git.tag import (
    CALVER,
    SEMVER,
    Scheme,
    create_tag,
    detect_scheme,
    fetch_tags,
    next_calver,
    next_semver,
    tags,
)


@click.command()
@click.option(
    "--calver",
    "scheme",
    flag_value=CALVER,
    default=None,
    help="Use calendar versioning (vYYYY.MM.N).",
)
@click.option(
    "--semver",
    "scheme",
    flag_value=SEMVER,
    default=None,
    help="Use semantic versioning (vMAJOR.MINOR.PATCH).",
)
@click.option(
    "--bump",
    type=click.Choice(["patch", "minor", "major"]),
    default=None,
    help="SemVer component to increment (ignored for CalVer). Prompted if not provided.",
)
@click.option("-y", "--yes", "confirmed", is_flag=True, help="Skip confirmation prompt.")
def release(scheme: Scheme | None, bump: str | None, confirmed: bool) -> None:
    """Tag origin/main and push the tag.

    Auto-detects CalVer or SemVer from existing tags. Prompts for scheme on
    first use. Pass --calver or --semver to skip the prompt.
    """
    fetch_tags()
    existing = tags()
    if not scheme:
        try:
            scheme = detect_scheme(existing)
        except ValueError as e:
            raise click.ClickException(str(e))
    if not scheme:
        click.echo("No existing tags found. Choose a versioning scheme:")
        click.echo(
            f"  {CALVER}   vYYYY.MM.N         — calendar versioning, counter resets each month"
        )
        click.echo(f"  {SEMVER}   vMAJOR.MINOR.PATCH — semantic versioning")
        raw = click.prompt(
            "Scheme", type=click.Choice([CALVER, SEMVER], case_sensitive=False), show_choices=False
        )
        scheme = CALVER if raw == CALVER else SEMVER
    if scheme == CALVER:
        tag = next_calver(existing, date.today())
    else:
        resolved_bump: str = bump or click.prompt(
            "Bump", type=click.Choice(["patch", "minor", "major"]), show_choices=True
        )
        tag = next_semver(existing, resolved_bump)
    if not confirmed:
        click.confirm(f"Tag and push {tag}", abort=True)
    create_tag(tag)
    click.echo(f"Tagged and pushed {tag}")
