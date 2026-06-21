import re

import click

from acta.cli.shared import TYPE_CHOICE, CLIGroup, open_editor
from acta.git.branch import fetch_origin, switch_new_branch
from acta.git.config import set_active_issue
from acta.github.issue import (
    IssueInfo,
    issue_close_not_planned,
    issue_create,
    issue_list,
    issue_view,
)
from acta.github.milestone import milestone_view


def slugify_title(title: str) -> str:
    """Turn an issue title into a short, branch-safe topic slug."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40].rstrip("-")


def compute_issue_column_widths(issues: list[IssueInfo]) -> tuple[int, int]:
    """Compute column widths (number, type) wide enough to align every issue in the set."""
    number_width = max((len(f"#{issue_info.number}") for issue_info in issues), default=1)
    type_width = max((len(issue_info.type or "—") for issue_info in issues), default=1)
    return number_width, type_width


def format_issue_lines(
    issues: list[IssueInfo],
    indent: str = "",
    widths: tuple[int, int] | None = None,
) -> list[str]:
    """Render issues as aligned lines, sorted by number.

    Pass `widths` to align against a wider set than `issues` (e.g. a whole board
    when rendering one milestone group); otherwise widths fit `issues` alone.
    """
    number_width, type_width = widths if widths is not None else compute_issue_column_widths(issues)
    return [
        f"{indent}{f'#{issue_info.number}':<{number_width}}  "
        f"{(issue_info.type or '—'):<{type_width}}  {issue_info.title}"
        for issue_info in sorted(issues, key=lambda issue_info: issue_info.number)
    ]


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
    if milestone_number is not None:
        for line in format_issue_lines(issues):
            click.echo(line)
        return
    issues_by_milestone: dict[int | None, list[IssueInfo]] = {}
    headers_by_milestone: dict[int | None, str] = {}
    for issue_info in issues:
        milestone_ref = issue_info.milestone
        milestone_key = milestone_ref.number if milestone_ref is not None else None
        issues_by_milestone.setdefault(milestone_key, []).append(issue_info)
        headers_by_milestone[milestone_key] = (
            f"#{milestone_ref.number} {milestone_ref.title}"
            if milestone_ref is not None
            else "No milestone"
        )
    widths = compute_issue_column_widths(issues)
    is_first_group = True
    for milestone_key in sorted(issues_by_milestone, key=lambda key: (key is None, key or 0)):
        if not is_first_group:
            click.echo()
        is_first_group = False
        click.echo(headers_by_milestone[milestone_key])
        for line in format_issue_lines(
            issues_by_milestone[milestone_key], indent="  ", widths=widths
        ):
            click.echo(line)


@issue.command(name="start")
@click.argument("number", type=int)
def start_issue(number: int) -> None:
    """Start work on an issue: create branch and record the active issue."""
    issue_info = issue_view(number)
    issue_type = issue_info.type
    milestone_ref = issue_info.milestone
    if milestone_ref is None:
        raise click.ClickException(
            f"Issue #{number} has no milestone — assign it to a milestone first"
        )
    milestone_detail = milestone_view(milestone_ref.number)
    scope = milestone_detail.scope
    if not scope:
        raise click.ClickException(
            f"Milestone #{milestone_ref.number} has no scope — "
            "its description must start with 'scope: SCOPE'"
        )
    slug = slugify_title(issue_info.title)
    topic = f"{number}-{slug}" if slug else str(number)
    branch_name = f"{issue_type}/{scope}/{topic}"
    fetch_origin()
    switch_new_branch(branch_name)
    set_active_issue(number)
    click.echo(f"On branch {branch_name}, active issue is #{number}.")
    issue_body = issue_info.body.strip()
    if issue_body:
        click.echo()
        click.echo(issue_body)


@issue.command(name="discard")
@click.argument("number", type=int)
def discard_issue(number: int) -> None:
    """Close an issue as discarded (not planned)."""
    issue_close_not_planned(number)
    click.echo(f"Issue #{number} discarded.")
