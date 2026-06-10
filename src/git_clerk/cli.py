import subprocess
import sys
from datetime import date

import click

from git_clerk import git
from git_clerk import github as gh
from git_clerk.branch import TYPES
from git_clerk.branch import parse as parse_branch
from git_clerk.release import CALVER, SEMVER, Scheme, detect_scheme, next_calver, next_semver

TYPE_CHOICE = click.Choice(sorted(TYPES))


class _Group(click.Group):
    def invoke(self, ctx: click.Context) -> object:
        try:
            return super().invoke(ctx)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)
        except RuntimeError as e:
            raise click.ClickException(str(e)) from e


def _strip_comments(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.startswith("#")).strip()


def _open_editor(hint: str) -> str:
    template = f"# {hint}\n# Lines starting with '#' are ignored.\n\n"
    raw = click.edit(template)
    result = _strip_comments(raw or "")
    if not result:
        raise click.Abort()
    return result


@click.group(cls=_Group, invoke_without_command=True)
@click.version_option(package_name="git-clerk")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Structured git workflow: conventional commits, trunk-based branches, GitHub PR lifecycle.

    Branch names follow the type/scope convention from the conventional commits specification.
    See https://www.conventionalcommits.org for the full spec.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.argument("name", metavar="TYPE/scope")
def branch(name: str) -> None:
    """Create a branch from origin/main."""
    try:
        parse_branch(name)
    except ValueError as e:
        raise click.ClickException(str(e))
    git.fetch_origin()
    git.switch_new_branch(name)


@main.command()
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
    br = git.current_branch()
    try:
        type_, scope = parse_branch(br)
    except ValueError as e:
        raise click.ClickException(str(e))
    header = f"{type_override or type_}({scope_override or scope}): {description}"
    if edit_body:
        body = _open_editor(header)
    if stage_all:
        git.add_all()
    git.commit(header, body)


@main.command()
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
    br = git.current_branch()
    try:
        type_, scope = parse_branch(br)
    except ValueError as e:
        raise click.ClickException(str(e))
    pr_title = f"{type_override or type_}({scope_override or scope}): {title}"
    if edit_body:
        body = _open_editor(f"{pr_title} ({br})")
    git.push_head()
    number, url = gh.pr_create(pr_title, body or "")
    click.echo(url)
    gh.pr_checks_watch(number)


@main.command()
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
    br = git.current_branch()
    if br == "main":
        raise click.ClickException("run 'git clerk ship' from the feature branch, not main")
    number, title = gh.pr_view()
    prompt = f'Ship "{title}" (#{number})'
    if update_branch:
        prompt += f", then update {update_branch}"
    if not confirmed:
        click.confirm(prompt, abort=True)
    if not gh.pr_checks_pass(number):
        raise click.ClickException(
            f"PR #{number} has failing or pending checks — run 'git clerk watch' to monitor"
        )
    gh.pr_merge(number)
    git.switch_main()
    git.pull_origin_main()
    if git.branch_exists(br):
        git.delete_branch(br)
    else:
        click.echo(f"warning: local branch '{br}' not found, skipping delete", err=True)
    if update_branch:
        git.switch_branch(update_branch)
        git.merge_origin_main()


@main.command()
def watch() -> None:
    """Watch CI checks for the current PR."""
    number, _ = gh.pr_view()
    gh.pr_checks_watch(number)


@main.command()
@click.option(
    "--calver",
    "scheme",
    flag_value=CALVER,
    default=None,
    help="Use calendar versioning (vYYYY.MM.N).",
)
@click.option(
    "--semver",
    "scheme",
    flag_value=SEMVER,
    default=None,
    help="Use semantic versioning (vMAJOR.MINOR.PATCH).",
)
@click.option(
    "--bump",
    type=click.Choice(["patch", "minor", "major"]),
    default=None,
    help="SemVer component to increment (ignored for CalVer). Prompted if not provided.",
)
@click.option("-y", "--yes", "confirmed", is_flag=True, help="Skip confirmation prompt.")
def release(scheme: Scheme | None, bump: str | None, confirmed: bool) -> None:
    """Tag origin/main and push the tag.

    Auto-detects CalVer or SemVer from existing tags. Prompts for scheme on
    first use. Pass --calver or --semver to skip the prompt.
    """
    git.fetch_tags()
    existing = git.tags()
    if not scheme:
        try:
            scheme = detect_scheme(existing)
        except ValueError as e:
            raise click.ClickException(str(e))
    if not scheme:
        click.echo("No existing tags found. Choose a versioning scheme:")
        click.echo(
            f"  {CALVER}   vYYYY.MM.N         — calendar versioning, counter resets each month"
        )
        click.echo(f"  {SEMVER}   vMAJOR.MINOR.PATCH — semantic versioning")
        raw = click.prompt(
            "Scheme", type=click.Choice([CALVER, SEMVER], case_sensitive=False), show_choices=False
        )
        scheme = CALVER if raw == CALVER else SEMVER
    if scheme == CALVER:
        tag = next_calver(existing, date.today())
    else:
        resolved_bump: str = bump or click.prompt(
            "Bump", type=click.Choice(["patch", "minor", "major"]), show_choices=True
        )
        tag = next_semver(existing, resolved_bump)
    if not confirmed:
        click.confirm(f"Tag and push {tag}", abort=True)
    git.create_tag(tag)
    click.echo(f"Tagged and pushed {tag}")
