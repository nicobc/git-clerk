import click

from gitclerk.git.branch import fetch_origin, switch_new_branch
from gitclerk.git.branch import parse as parse_branch


@click.command()
@click.argument("name", metavar="TYPE/scope")
def branch(name: str) -> None:
    """Create a branch from origin/main."""
    try:
        parse_branch(name)
    except ValueError as error:
        raise click.ClickException(str(error))
    fetch_origin()
    switch_new_branch(name)
    click.echo(f"Branched {name} from origin/main.")
