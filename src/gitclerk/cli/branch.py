import click

from gitclerk.git.branch import fetch_origin, switch_new_branch
from gitclerk.git.branch import parse as parse_branch


@click.command()
@click.argument("name", metavar="TYPE/scope")
def branch(name: str) -> None:
    """Create a branch from origin/main."""
    try:
        parse_branch(name)
    except ValueError as e:
        raise click.ClickException(str(e))
    fetch_origin()
    switch_new_branch(name)
