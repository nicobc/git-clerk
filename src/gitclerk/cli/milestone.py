import click

from gitclerk.cli.shared import CLIGroup, open_editor
from gitclerk.github import repo
from gitclerk.github.milestone import (
    MilestoneListItem,
    milestone_create,
    milestone_list,
    milestone_reopen,
)


def get_repo_name() -> str:
    return repo().split("/")[-1]


def format_milestone_line(milestone_list_item: MilestoneListItem) -> str:
    noun = "issue" if milestone_list_item.open_issues == 1 else "issues"
    closed = (
        f", {milestone_list_item.closed_issues} closed" if milestone_list_item.closed_issues else ""
    )
    return (
        f"#{milestone_list_item.number}  {milestone_list_item.title} — "
        f"{milestone_list_item.open_issues} {noun} open{closed}"
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
    click.echo(f"{get_repo_name()} milestones:")
    for milestone_list_item in milestones:
        click.echo(format_milestone_line(milestone_list_item))


@milestone.command(name="reopen")
@click.argument("number", type=int)
def reopen_milestone(number: int) -> None:
    """Reopen a closed milestone."""
    milestone_reopen(number)
    click.echo(f"Milestone #{number} reopened.")
