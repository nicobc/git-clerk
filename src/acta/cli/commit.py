import click

from acta.cli.shared import TYPE_CHOICE, open_editor
from acta.git.branch import get_current_branch
from acta.git.branch import parse as parse_branch
from acta.git.commit import add_all, push_head
from acta.git.commit import commit as git_commit


@click.command()
@click.option(
    "-A", "--stage-all", "stage_all", is_flag=True, help="Stage all changes before committing."
)
@click.option("-P", "--push", "push", is_flag=True, help="Push to origin after committing.")
@click.option(
    "-t",
    "--type",
    "type_override",
    default=None,
    metavar="TYPE",
    type=TYPE_CHOICE,
    help="Override the commit type inferred from the branch name.",
)
@click.option(
    "-s",
    "--scope",
    "scope_override",
    default=None,
    help="Override the commit scope inferred from the branch name.",
)
@click.option("-b", "--body", "body", default=None, help="Commit body. Mutually exclusive with -e.")
@click.option("-e", "--edit", "edit_body", is_flag=True, help="Open $EDITOR for commit body.")
@click.argument("description")
def commit(
    stage_all: bool,
    push: bool,
    type_override: str | None,
    scope_override: str | None,
    body: str | None,
    edit_body: bool,
    description: str,
) -> None:
    """Create a conventional commit from the branch name.

    Type and scope are derived from the branch. By default no body is added —
    pass -b for an inline body, or -e to open $EDITOR. -b and -e are mutually
    exclusive.
    """
    if body and edit_body:
        raise click.UsageError("--body and --edit are mutually exclusive")
    branch_name = get_current_branch()
    try:
        type_, scope = parse_branch(branch_name)
    except ValueError as error:
        raise click.ClickException(str(error))
    header = f"{type_override or type_}({scope_override or scope}): {description}"
    if edit_body:
        body = open_editor(header)
    if stage_all:
        add_all()
    git_commit(header, body)
    if push:
        push_head()
        click.echo("Pushed. If a PR is open, refresh its description: gh pr edit")
