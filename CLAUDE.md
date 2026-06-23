# git-acta

Structured git workflow CLI: conventional commits, trunk-based branches, GitHub PR lifecycle. Thin Click CLI (`src/acta/cli/`) over git (`src/acta/git/`) and GitHub (`src/acta/github/`) helpers; every subprocess call routes through the `git()`/`gh()` wrappers.

## MUST DO — enforce on every task without exception

**MUST BE OPINIONATED, NOT SYCOPHANTIC.** Push back on bad ideas; explain the better path instead of silently complying.

**MUST DOGFOOD `acta` PER `CONTRIBUTING.md`.** Drive every branch/commit/PR/ship through `acta`, never raw `git`/`gh` for those steps.

**MUST APPLY DESIGN PRINCIPLES ON EVERY CHANGE.** KISS, YAGNI, DRY, less-is-more, Unix do-one-thing.

**MUST DOCSTRING EVERY FUNCTION (Google style).** One line minimum; full Args/Returns/Raises plus a behavioral example for non-obvious ones. A wrapper's docstring states what its underlying `git`/`gh` command does and why.

**MUST TYPE EVERYTHING AND KEEP PYRIGHT-STRICT CLEAN.** Full annotations, no implicit `Any`.

**MUST TEST EVERY BEHAVIOR CHANGE.** pytest with `pytest-subprocess`: real `git` against a temp repo, `gh` faked via `fp.register`. Mirror the existing `tests/` patterns. Use `uv run pytest` to run the tests.

**LINT AND TYPES RUN ON COMMIT** (ruff + pyright via the pre-commit hook) — rely on the hook, don't run them manually.
