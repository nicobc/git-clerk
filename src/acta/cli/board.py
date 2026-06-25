"""``acta board`` — a session snapshot of active work and milestones."""

import click

from acta.cli.issue import format_issue_lines
from acta.cli.milestone import format_milestone_line
from acta.git.branch import get_current_branch
from acta.git.commit import get_commit_subjects, get_working_tree_changes
from acta.git.state import get_branch_issue
from acta.github.issue import issue_list, issue_view
from acta.github.milestone import milestone_list


@click.command()
def board() -> None:
    """Session snapshot: active work, current milestone, and backlog."""
    branch_name = get_current_branch()
    click.echo(f"Current branch: {branch_name}")
    active_issue_number = get_branch_issue(branch_name)
    focus_milestone_number: int | None = None
    if active_issue_number is not None:
        active_issue = issue_view(active_issue_number)
        click.echo(f"Active issue: #{active_issue_number} {active_issue.title}")
        focus_milestone_number = (
            active_issue.milestone.number if active_issue.milestone is not None else None
        )

    changes = get_working_tree_changes()
    if changes:
        click.echo()
        click.echo("Working tree:")
        for change_line in changes:
            click.echo(change_line)

    unpushed = get_commit_subjects("origin/main..HEAD")
    if unpushed:
        click.echo()
        click.echo("Unpushed commits:")
        for subject in unpushed:
            click.echo(subject)

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
