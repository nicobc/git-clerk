import click

from gitclerk.cli.shared import TYPE_CHOICE, CLIGroup, open_editor
from gitclerk.git.branch import fetch_origin, switch_new_branch
from gitclerk.git.config import set_active_issue
from gitclerk.github.issue import issue_close_not_planned, issue_create, issue_list, issue_view
from gitclerk.github.milestone import milestone_view


@click.group(cls=CLIGroup)
def issue() -> None:
    """Manage issues."""


@issue.command(name="new")
@click.argument("title")
@click.argument("body", required=False, default=None)
@click.option("--type", "type_", required=True, type=TYPE_CHOICE, help="Issue type label.")
@click.option(
    "--milestone",
    "milestone_number",
    default=None,
    type=int,
    metavar="NUMBER",
    help="Milestone number.",
)
@click.option("-e", "--edit", "edit_body", is_flag=True, help="Open $EDITOR for the issue body.")
def new_issue(
    title: str,
    body: str | None,
    type_: str,
    milestone_number: int | None,
    edit_body: bool,
) -> None:
    """Create a new issue."""
    if body and edit_body:
        raise click.UsageError("BODY and --edit are mutually exclusive")
    if edit_body:
        body = open_editor(title)
    number = issue_create(title, type_, body or "", milestone_number)
    click.echo(f"Issue #{number} created.")


@issue.command(name="list")
@click.option(
    "--milestone",
    "milestone_number",
    default=None,
    type=int,
    metavar="NUMBER",
    help="Filter by milestone number.",
)
def list_issues(milestone_number: int | None) -> None:
    """List open issues."""
    issues = issue_list(milestone_number)
    if not issues:
        click.echo("No open issues.")
        return
    for i in issues:
        ms = i.milestone
        ms_str = f"milestone #{ms.number}" if ms is not None else "no milestone"
        type_label = i.type or "—"
        click.echo(f"#{i.number} [{type_label}] [{ms_str}] {i.title}")


@issue.command(name="start")
@click.argument("number", type=int)
def start_issue(number: int) -> None:
    """Start work on an issue: create branch and record the active issue."""
    issue_data = issue_view(number)
    type_ = issue_data.type
    ms = issue_data.milestone
    if ms is None:
        raise click.ClickException(
            f"Issue #{number} has no milestone — assign it to a milestone first"
        )
    m = milestone_view(ms.number)
    scope = m.scope
    if not scope:
        raise click.ClickException(
            f"Milestone #{ms.number} has no scope — its description must start with 'scope: SCOPE'"
        )
    branch_name = f"{type_}/{scope}"
    fetch_origin()
    switch_new_branch(branch_name)
    set_active_issue(number)
    click.echo(f"On branch '{branch_name}', active issue is #{number}.")


@issue.command(name="discard")
@click.argument("number", type=int)
def discard_issue(number: int) -> None:
    """Close an issue as discarded (not planned)."""
    issue_close_not_planned(number)
    click.echo(f"Issue #{number} discarded.")
