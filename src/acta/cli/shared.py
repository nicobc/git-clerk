import re
import subprocess
import sys

import click

from acta.git.branch import TYPES

# A leading conventional-commit prefix: type, optional (scope), optional !, colon.
_TYPE_PREFIX_RE = re.compile(rf"^(?:{'|'.join(sorted(TYPES))})(?:\([^)]*\))?!?:\s*")


class CLIGroup(click.Group):
    def invoke(self, ctx: click.Context) -> object:
        try:
            return super().invoke(ctx)
        except (click.exceptions.Exit, click.exceptions.Abort):
            raise  # Click's own control flow (--help, ctrl-C); both subclass RuntimeError
        except subprocess.CalledProcessError as error:
            if error.stderr:
                click.echo(error.stderr, err=True, nl=False)
            sys.exit(error.returncode)
        except RuntimeError as error:
            raise click.ClickException(str(error)) from error


def strip_comments(text: str) -> str:
    lines = [line for line in text.splitlines() if not line.startswith("#")]
    collapsed: list[str] = []
    prev_blank = False
    for line in lines:
        blank = not line.strip()
        if blank and prev_blank:
            continue
        collapsed.append(line)
        prev_blank = blank
    return "\n".join(collapsed).strip()


def open_editor(hint: str) -> str:
    template = f"# {hint}\n# Lines starting with '#' are ignored.\n\n"
    edited_text = click.edit(template)
    body_text = strip_comments(edited_text or "")
    if not body_text:
        raise click.Abort()
    return body_text


def strip_type_prefix(title: str) -> str:
    """Drop a redundant leading conventional-commit prefix from a caller title.

    acta derives type(scope) from the branch and prepends it, so a prefix the
    caller typed (e.g. 'fix: x' or 'fix(auth)!: x') would otherwise double up.
    """
    return _TYPE_PREFIX_RE.sub("", title, count=1)


TYPE_CHOICE = click.Choice(sorted(TYPES))
