import click

from gitclerk.cli.branch import branch
from gitclerk.cli.commit import commit
from gitclerk.cli.issue import issue
from gitclerk.cli.milestone import milestone
from gitclerk.cli.pr import pr, ship, watch
from gitclerk.cli.release import release
from gitclerk.cli.shared import CLIGroup


@click.group(cls=CLIGroup, invoke_without_command=True)
@click.version_option(package_name="git-clerk")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Structured git workflow: conventional commits, trunk-based branches, GitHub PR lifecycle.

    Branch names follow the type/scope convention from the conventional commits specification.
    See https://www.conventionalcommits.org for the full spec.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


main.add_command(branch)
main.add_command(commit)
main.add_command(pr)
main.add_command(ship)
main.add_command(watch)
main.add_command(release)
main.add_command(milestone)
main.add_command(issue)
