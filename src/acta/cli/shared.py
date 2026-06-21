import subprocess
import sys

import click

from acta.git.branch import TYPES


class CLIGroup(click.Group):
    def invoke(self, ctx: click.Context) -> object:
        try:
            return super().invoke(ctx)
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


TYPE_CHOICE = click.Choice(sorted(TYPES))
