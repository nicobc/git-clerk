import click

from acta.cli.board import board
from acta.cli.branch import branch
from acta.cli.commit import commit
from acta.cli.issue import issue
from acta.cli.milestone import milestone
from acta.cli.pr import pr, ship, watch
from acta.cli.release import release
from acta.cli.shared import CLIGroup


@click.group(cls=CLIGroup, invoke_without_command=True)
@click.version_option(package_name="git-acta")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Structured git workflow: conventional commits, trunk-based branches, GitHub PR lifecycle.

    Branch names follow the type/scope convention from the conventional commits specification.
    See https://www.conventionalcommits.org for the full spec.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


main.add_command(board)
main.add_command(branch)
main.add_command(commit)
main.add_command(pr)
main.add_command(ship)
main.add_command(watch)
main.add_command(release)
main.add_command(milestone)
main.add_command(issue)
