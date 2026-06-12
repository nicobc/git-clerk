import click

from gitclerk.cli.shared import CLIGroup, open_editor
from gitclerk.github.milestone import (
    milestone_create,
    milestone_list,
    milestone_reopen,
)


@click.group(cls=CLIGroup)
def milestone() -> None:
    """Manage milestones."""


@milestone.command(name="new")
@click.argument("title")
@click.argument("description", required=False, default=None)
@click.option("--scope", required=True, help="Scope used for branch names in this milestone.")
@click.option("-e", "--edit", "edit_body", is_flag=True, help="Open $EDITOR for the description.")
def new_milestone(title: str, description: str | None, scope: str, edit_body: bool) -> None:
    """Create a new milestone."""
    if description and edit_body:
        raise click.UsageError("DESCRIPTION and --edit are mutually exclusive")
    if edit_body:
        description = open_editor(title)
    number = milestone_create(title, scope, description or "")
    click.echo(f"Milestone #{number} created.")


@milestone.command(name="list")
def list_milestones() -> None:
    """List open milestones."""
    milestones = milestone_list()
    if not milestones:
        click.echo("No open milestones.")
        return
    for m in milestones:
        scope = m.scope or "—"
        click.echo(
            f"#{m.number} {m.title} scope: {scope} [{m.open_issues} open, {m.closed_issues} closed]"
        )


@milestone.command(name="reopen")
@click.argument("number", type=int)
def reopen_milestone(number: int) -> None:
    """Reopen a closed milestone."""
    milestone_reopen(number)
    click.echo(f"Milestone #{number} reopened.")
