import click

from gitclerk.cli.shared import CLIGroup
from gitclerk.github.label import ensure_type_labels


@click.group(cls=CLIGroup)
def board() -> None:
    """Manage the project board."""


@board.command(name="setup")
def board_setup() -> None:
    """Create type labels in the repo (idempotent)."""
    ensure_type_labels()
    click.echo("Board labels ready.")
