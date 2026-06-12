import subprocess
import sys

import click

from gitclerk.git.branch import TYPES


class CLIGroup(click.Group):
    def invoke(self, ctx: click.Context) -> object:
        try:
            return super().invoke(ctx)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)
        except RuntimeError as e:
            raise click.ClickException(str(e)) from e


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
    raw = click.edit(template)
    result = strip_comments(raw or "")
    if not result:
        raise click.Abort()
    return result


TYPE_CHOICE = click.Choice(sorted(TYPES))
