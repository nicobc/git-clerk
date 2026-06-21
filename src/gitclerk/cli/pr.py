import click

from gitclerk.cli.shared import TYPE_CHOICE, open_editor
from gitclerk.git.branch import (
    delete_branch,
    get_current_branch,
    merge_origin_main,
    pull_origin_main,
    switch_branch,
    switch_main,
)
from gitclerk.git.branch import parse as parse_branch
from gitclerk.git.commit import push_head
from gitclerk.git.config import clear_active_issue, get_active_issue
from gitclerk.github.issue import issue_view
from gitclerk.github.milestone import milestone_close, milestone_view
from gitclerk.github.pr import pr_checks_pass, pr_checks_watch, pr_create, pr_merge, pr_view


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
@click.option("-e", "--edit", "edit_body", is_flag=True, help="Open $EDITOR for the PR body.")
@click.option(
    "--breaking",
    is_flag=True,
    help="Mark a breaking change: append '!' to type(scope) per conventional commits.",
)
@click.argument("title")
@click.argument("body", required=False, default=None)
def pr(
    type_override: str | None,
    scope_override: str | None,
    edit_body: bool,
    breaking: bool,
    title: str,
    body: str | None,
) -> None:
    """Push branch, open a PR against main, and watch CI.

    By default no body is added — pass BODY as a second argument for an inline
    body, or use -e to open $EDITOR. BODY and -e are mutually exclusive.
    """
    if body and edit_body:
        raise click.UsageError("BODY and --edit are mutually exclusive")
    branch_name = get_current_branch()
    try:
        type_, scope = parse_branch(branch_name)
    except ValueError as error:
        raise click.ClickException(str(error))
    breaking_marker = "!" if breaking else ""
    pr_title = f"{type_override or type_}({scope_override or scope}){breaking_marker}: {title}"
    if edit_body:
        body = open_editor(f"{pr_title} ({branch_name})")
    active_issue_number = get_active_issue()
    if active_issue_number is not None:
        closes_footer = f"Closes #{active_issue_number}"
        body = f"{body}\n\n{closes_footer}" if body else closes_footer
    push_head()
    number, url = pr_create(pr_title, body or "")
    click.echo(url)
    pr_checks_watch(number)


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
        raise click.ClickException("run 'git clerk ship' from the feature branch, not main")
    pr_number, title = pr_view()
    prompt = f'Ship "{title}" (#{pr_number})'
    if update_branch:
        prompt += f", then update {update_branch}"
    if not confirmed:
        click.confirm(prompt, abort=True)
    if not pr_checks_pass(pr_number):
        raise click.ClickException(
            f"PR #{pr_number} has failing or pending checks — run 'git clerk watch' to monitor"
        )
    active_issue_number = get_active_issue()
    milestone_number: int | None = None
    if active_issue_number is not None:
        active_issue = issue_view(active_issue_number)
        milestone_ref = active_issue.milestone
        if milestone_ref is not None:
            milestone_number = milestone_ref.number
    pr_merge(pr_number)
    switch_main()
    pull_origin_main()
    delete_branch(branch_name)
    if update_branch:
        switch_branch(update_branch)
        merge_origin_main()
    if active_issue_number is not None:
        clear_active_issue()
    if milestone_number is not None:
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
    pr_checks_watch(number)
