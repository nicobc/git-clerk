import click

from gitclerk.cli.issue import format_issue_lines
from gitclerk.cli.milestone import format_milestone_line
from gitclerk.git.branch import current_branch
from gitclerk.git.config import get_active_issue
from gitclerk.github.issue import issue_list, issue_view
from gitclerk.github.milestone import milestone_list


@click.command()
def board() -> None:
    """Session snapshot: active work, current milestone, and backlog."""
    branch_name = current_branch()
    click.echo(f"Current branch: {branch_name}")
    active_issue_number = get_active_issue()
    focus_milestone_number: int | None = None
    if active_issue_number is not None:
        active_issue = issue_view(active_issue_number)
        click.echo(f"Active issue: #{active_issue_number} {active_issue.title}")
        focus_milestone_number = (
            active_issue.milestone.number if active_issue.milestone is not None else None
        )

    milestones = milestone_list()
    if not milestones:
        click.echo()
        click.echo("No open milestones.")
        return

    if focus_milestone_number is None:
        focus_milestone_number = milestones[0].number
    focus_milestone = next(
        (
            milestone_list_item
            for milestone_list_item in milestones
            if milestone_list_item.number == focus_milestone_number
        ),
        None,
    )

    if focus_milestone is not None:
        click.echo()
        click.echo(format_milestone_line(focus_milestone))
        for line in format_issue_lines(issue_list(focus_milestone.number), indent="  "):
            click.echo(line)

    remaining_milestones = [
        milestone_list_item
        for milestone_list_item in milestones
        if milestone_list_item.number != focus_milestone_number
    ]
    if remaining_milestones:
        click.echo()
        for milestone_list_item in remaining_milestones:
            click.echo(format_milestone_line(milestone_list_item))
