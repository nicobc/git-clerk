import click

from gitclerk.cli.shared import TYPE_CHOICE, open_editor
from gitclerk.git.branch import (
    current_branch,
    delete_branch,
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
@click.argument("title")
@click.argument("body", required=False, default=None)
def pr(
    type_override: str | None,
    scope_override: str | None,
    edit_body: bool,
    title: str,
    body: str | None,
) -> None:
    """Push branch, open a PR against main, and watch CI.

    By default no body is added — pass BODY as a second argument for an inline
    body, or use -e to open $EDITOR. BODY and -e are mutually exclusive.
    """
    if body and edit_body:
        raise click.UsageError("BODY and --edit are mutually exclusive")
    br = current_branch()
    try:
        type_, scope = parse_branch(br)
    except ValueError as e:
        raise click.ClickException(str(e))
    pr_title = f"{type_override or type_}({scope_override or scope}): {title}"
    if edit_body:
        body = open_editor(f"{pr_title} ({br})")
    active = get_active_issue()
    if active is not None:
        closes = f"Closes #{active}"
        body = f"{body}\n\n{closes}" if body else closes
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
    br = current_branch()
    if br == "main":
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
    active = get_active_issue()
    milestone_number: int | None = None
    if active is not None:
        issue_data = issue_view(active)
        ms = issue_data.milestone
        if ms is not None:
            milestone_number = ms.number
    pr_merge(pr_number)
    switch_main()
    pull_origin_main()
    delete_branch(br)
    if update_branch:
        switch_branch(update_branch)
        merge_origin_main()
    if active is not None:
        clear_active_issue()
    if milestone_number is not None:
        m = milestone_view(milestone_number)
        if m.open_issues == 0:
            milestone_close(milestone_number)
            click.echo(f'Milestone #{milestone_number} "{m.title}" completed and closed.')


@click.command()
def watch() -> None:
    """Watch CI checks for the current PR."""
    number, _ = pr_view()
    pr_checks_watch(number)
