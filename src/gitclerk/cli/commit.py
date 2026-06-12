import click

from gitclerk.cli.shared import TYPE_CHOICE, open_editor
from gitclerk.git.branch import current_branch
from gitclerk.git.branch import parse as parse_branch
from gitclerk.git.commit import add_all
from gitclerk.git.commit import commit as git_commit


@click.command()
@click.option("-A", "stage_all", is_flag=True, help="Stage all changes before committing.")
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
@click.option("-e", "--edit", "edit_body", is_flag=True, help="Open $EDITOR for commit body.")
@click.argument("description")
@click.argument("body", required=False, default=None)
def commit(
    stage_all: bool,
    type_override: str | None,
    scope_override: str | None,
    edit_body: bool,
    description: str,
    body: str | None,
) -> None:
    """Create a conventional commit from the branch name.

    Type and scope are derived from the branch. By default no body is added —
    pass BODY as a second argument for an inline body, or use -e to open $EDITOR.
    BODY and -e are mutually exclusive.
    """
    if body and edit_body:
        raise click.UsageError("BODY and --edit are mutually exclusive")
    br = current_branch()
    try:
        type_, scope = parse_branch(br)
    except ValueError as e:
        raise click.ClickException(str(e))
    header = f"{type_override or type_}({scope_override or scope}): {description}"
    if edit_body:
        body = open_editor(header)
    if stage_all:
        add_all()
    git_commit(header, body)
