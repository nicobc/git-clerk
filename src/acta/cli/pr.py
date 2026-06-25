"""``acta pr``, ``ship``, and ``watch`` — the pull-request lifecycle."""

import click

from acta.cli.checks import watch_checks
from acta.cli.shared import TYPE_CHOICE, open_editor, strip_type_prefix
from acta.git.branch import (
    delete_branch,
    get_current_branch,
    merge_origin_main,
    prune_origin,
    pull_origin_main,
    switch_branch,
    switch_main,
)
from acta.git.branch import parse as parse_branch
from acta.git.commit import push_head
from acta.git.state import clear_branch, get_branch_issue, set_branch_pr
from acta.github.issue import issue_view
from acta.github.milestone import milestone_close, milestone_view
from acta.github.pr import pr_checks_pass, pr_closing_issues, pr_create, pr_merge, pr_view


@click.command()
@click.option(
    "-t",
    "--type",
    "type_override",
    default=None,
    metavar="TYPE",
    type=TYPE_CHOICE,
    help="Override the PR title type inferred from the branch name.",
)
@click.option(
    "-s",
    "--scope",
    "scope_override",
    default=None,
    help="Override the PR title scope inferred from the branch name.",
)
@click.option("-b", "--body", "body", default=None, help="PR body. Mutually exclusive with -e.")
@click.option("-e", "--edit", "edit_body", is_flag=True, help="Open $EDITOR for the PR body.")
@click.option(
    "--breaking",
    is_flag=True,
    help="Mark a breaking change: append '!' to type(scope) per conventional commits.",
)
@click.argument("title")
def pr(
    type_override: str | None,
    scope_override: str | None,
    body: str | None,
    edit_body: bool,
    breaking: bool,
    title: str,
) -> None:
    """Push branch, open a PR against main, and watch CI.

    By default no body is added — pass -b for an inline body, or -e to open
    $EDITOR. -b and -e are mutually exclusive.
    """
    if body and edit_body:
        raise click.UsageError("--body and --edit are mutually exclusive")
    branch_name = get_current_branch()
    try:
        type_, scope = parse_branch(branch_name)
    except ValueError as error:
        raise click.ClickException(str(error))
    breaking_marker = "!" if breaking else ""
    pr_title = (
        f"{type_override or type_}({scope_override or scope}){breaking_marker}: "
        f"{strip_type_prefix(title)}"
    )
    if edit_body:
        body = open_editor(f"{pr_title} ({branch_name})")
    issue_number = get_branch_issue(branch_name)
    if issue_number is not None:
        closes_footer = f"Closes #{issue_number}"
        body = f"{body}\n\n{closes_footer}" if body else closes_footer
    push_head()
    number, url = pr_create(pr_title, body or "")
    set_branch_pr(branch_name, number)
    click.echo(f"Opened PR #{number} at {url}")
    watch_checks(number)


@click.command()
@click.option(
    "-u",
    "--update",
    "update_branch",
    default=None,
    metavar="BRANCH",
    help="After shipping, switch to BRANCH and merge origin/main.",
)
@click.option("-y", "--yes", "confirmed", is_flag=True, help="Skip confirmation prompt.")
def ship(update_branch: str | None, confirmed: bool) -> None:
    """Ship the PR and return to a clean main.

    Squash-merges the current branch's PR, deletes the remote branch, switches
    to local main, pulls, and force-deletes the local branch.
    """
    branch_name = get_current_branch()
    if branch_name == "main":
        raise click.ClickException("run 'acta ship' from the feature branch, not main")
    pr_number, title = pr_view()
    prompt = f'Ship "{title}" (#{pr_number})'
    if update_branch:
        prompt += f", then update {update_branch}"
    if not confirmed:
        click.confirm(prompt, abort=True)
    if not pr_checks_pass(pr_number):
        raise click.ClickException(
            f"PR #{pr_number} has failing or pending checks — run 'acta watch' to monitor"
        )
    # The issues (and their milestones) to act on come from the ones this PR
    # closes, per GitHub's own linkage, so an unlinked PR touches nothing.
    closing_issue_numbers = sorted(pr_closing_issues(pr_number))
    milestone_numbers: set[int] = set()
    for issue_number in closing_issue_numbers:
        closing_issue = issue_view(issue_number)
        if closing_issue.milestone is not None:
            milestone_numbers.add(closing_issue.milestone.number)
    pr_merge(pr_number)
    click.echo(f"Merged PR #{pr_number} {branch_name} → main")
    if closing_issue_numbers:
        refs = ", ".join(f"#{number}" for number in closing_issue_numbers)
        noun = "issue" if len(closing_issue_numbers) == 1 else "issues"
        click.echo(f"Closed {noun} {refs}.")
    switch_main()
    pull_origin_main()
    delete_branch(branch_name)
    prune_origin()
    click.echo(
        f"Switched to main, pulled origin/main, deleted {branch_name}, and pruned stale refs."
    )
    clear_branch(branch_name)
    if update_branch:
        switch_branch(update_branch)
        merge_origin_main()
        click.echo(f"Switched to {update_branch}, merged origin/main.")
    for milestone_number in sorted(milestone_numbers):
        milestone_detail = milestone_view(milestone_number)
        if milestone_detail.open_issues == 0:
            milestone_close(milestone_number)
            click.echo(
                f'Milestone #{milestone_number} "{milestone_detail.title}" completed and closed.'
            )


@click.command()
def watch() -> None:
    """Watch CI checks for the current PR."""
    number, _ = pr_view()
    watch_checks(number)
