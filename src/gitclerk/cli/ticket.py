import click

from gitclerk.cli.shared import TYPE_CHOICE, CLIGroup, open_editor
from gitclerk.git.branch import fetch_origin, switch_new_branch
from gitclerk.git.config import set_active_issue
from gitclerk.github.issue import issue_close_not_planned, issue_create, issue_list, issue_view
from gitclerk.github.milestone import milestone_view


@click.group(cls=CLIGroup)
def ticket() -> None:
    """Manage tickets (GitHub Issues)."""


@ticket.command(name="new")
@click.argument("title")
@click.argument("body", required=False, default=None)
@click.option("--type", "type_", default=None, type=TYPE_CHOICE, help="Ticket type label.")
@click.option(
    "--epic",
    "epic_number",
    default=None,
    type=int,
    metavar="NUMBER",
    help="Epic (milestone) number.",
)
@click.option("-e", "--edit", "edit_body", is_flag=True, help="Open $EDITOR for the ticket body.")
def ticket_new(
    title: str,
    body: str | None,
    type_: str | None,
    epic_number: int | None,
    edit_body: bool,
) -> None:
    """Create a new ticket."""
    if body and edit_body:
        raise click.UsageError("BODY and --edit are mutually exclusive")
    if edit_body:
        body = open_editor(title)
    number = issue_create(title, body or "", type_, epic_number)
    click.echo(f"Ticket #{number} created.")


@ticket.command(name="list")
@click.option(
    "--epic",
    "epic_number",
    default=None,
    type=int,
    metavar="NUMBER",
    help="Filter by epic (milestone) number.",
)
def ticket_list(epic_number: int | None) -> None:
    """List open tickets."""
    issues = issue_list(epic_number)
    if not issues:
        click.echo("No open tickets.")
        return
    for i in issues:
        ms = i.milestone
        epic_str = f"epic #{ms.number}" if ms is not None else "no epic"
        type_label = i.type or "—"
        click.echo(f"#{i.number:<4} [{type_label:<10}] [{epic_str:<12}] {i.title}")


@ticket.command(name="start")
@click.argument("number", type=int)
def ticket_start(number: int) -> None:
    """Start work on a ticket: create branch and record the active issue."""
    issue_data = issue_view(number)
    type_ = issue_data.type
    if type_ is None:
        raise click.ClickException(
            f"Ticket #{number} has no type label — run 'git clerk board setup' and label it"
        )
    ms = issue_data.milestone
    if ms is None:
        raise click.ClickException(f"Ticket #{number} has no epic — assign it to an epic first")
    m = milestone_view(ms.number)
    scope = m.scope
    if not scope:
        raise click.ClickException(
            f"Epic #{ms.number} has no scope — its description must start with 'scope: SCOPE'"
        )
    branch_name = f"{type_}/{scope}"
    fetch_origin()
    switch_new_branch(branch_name)
    set_active_issue(number)
    click.echo(f"On branch '{branch_name}', active issue is #{number}.")


@ticket.command(name="discard")
@click.argument("number", type=int)
def ticket_discard(number: int) -> None:
    """Close a ticket as discarded (not planned)."""
    issue_close_not_planned(number)
    click.echo(f"Ticket #{number} discarded.")
