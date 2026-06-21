# git-clerk

[![PyPI version](https://img.shields.io/pypi/v/git-clerk)](https://pypi.org/project/git-clerk/)
[![Python versions](https://img.shields.io/pypi/pyversions/git-clerk)](https://pypi.org/project/git-clerk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/nicobc/git-clerk/actions/workflows/test.yml/badge.svg)](https://github.com/nicobc/git-clerk/actions/workflows/test.yml)

A structured git workflow CLI for [conventional commits](https://www.conventionalcommits.org/), trunk-based branching, and a clean GitHub PR lifecycle — all from the command line.

## Philosophy

git-clerk is built on three practices that reinforce each other: [trunk-based development](https://trunkbaseddevelopment.com/), [conventional commits](https://www.conventionalcommits.org/), and squash-merge-only history. Short-lived branches stay close to `main`. Squash merges keep `main`'s history linear and readable — one commit per feature. Conventional commit types make that history meaningful at a glance. git-clerk connects all three as a unit: you name your branch `feat/user-auth` once, and every commit message, PR title, and release tag follows from that single decision.

## Opinions

git-clerk is intentionally opinionated. These constraints are not configurable:

- **GitHub only** — PR and release operations rely on `gh`. GitLab and Bitbucket are not supported.
- **Squash merges** — `ship` always squash-merges to keep `main`'s history linear.
- **Single trunk** — `main` is the only integration branch. `develop`, `release/*`, and similar long-lived branches are out of scope. The trunk name is not configurable — repositories using a different default branch are not supported.
- **Conventional commits** — branch names must follow `type/scope` using one of the [11 standard types](https://www.conventionalcommits.org).

If your workflow diverges from any of these, git-clerk is not the right tool.

## Prerequisites

**Local**

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for installation
- [GitHub CLI](https://cli.github.com/) (`gh`) 2.0 or later, authenticated to your GitHub account

**Repository configuration**

git-clerk assumes the repository is configured to match its workflow. Without this, the tool still works but its guarantees don't hold — anyone can bypass conventions by using `git` and `gh` directly.

Ask your infra or platform team to configure:

- **Squash merges only** — disable merge commits and rebase merges so `main` stays linear
- **Branch protection on `main`** — require pull requests before merging; disallow direct pushes
- **Required status checks** — require CI to pass before a PR can be merged; this makes `git clerk ship`'s CI gate structural rather than advisory

## Installation

```sh
uv tool install git-clerk
```

To use it as `git clerk` (recommended) rather than `git-clerk`, register a git alias:

```sh
git config --global alias.clerk '!git-clerk'
```

After this, `git clerk` prints help and `git clerk commit --help` (any subcommand) works as expected. Note that `git clerk --help` will not work — git intercepts `--help` before running the alias and tries to open a man page. Use `git clerk` or `git-clerk --help` for top-level help instead.

## Workflow walkthrough

Here is a complete cycle from starting a feature to tagging a release.

**1. Create a branch**

```sh
git clerk branch feat/user-auth
```

Fetches the latest `origin/main` and creates `feat/user-auth` from it. The branch name is the only thing you decide upfront — type and scope flow into every subsequent command automatically.

**2. Do your work, then commit**

```sh
git clerk commit -A "add login form"
```

Stages all changes and commits with the message `feat(user-auth): add login form`. The type and scope come from the branch name — you only write the description.

For commits that need more context, pass the body as a second argument or open your editor with `-e`:

```sh
git clerk commit -A "add login form" "Supports email and SSO providers."
# → commits with inline body (useful in scripts and LLM workflows)

git clerk commit -A -e "add login form"
# → opens $EDITOR for the body, then commits
```

You can commit as many times as you want. Only the squash commit that lands on `main` is permanent.

**3. Open a PR**

```sh
git clerk pr "Add login form"
```

Pushes the branch with upstream tracking set, creates the PR against `main`, prints the URL, then watches CI checks until they complete. You can share the URL while CI is still running.

By default no body is added. To add one:

```sh
git clerk pr "Add login form" "Adds email/password and SSO login. Closes #42."
# inline body

git clerk pr -e "Add login form"
# opens $EDITOR for the body
```

**4. Ship it**

Once CI is green:

```sh
git clerk ship
```

Shows you the PR title and number, asks for confirmation, then: squash-merges into `main`, deletes the remote branch, switches to local `main`, pulls, and force-deletes the local branch. You end up on a clean, up-to-date `main` in one step.

**5. Tag a release**

```sh
git clerk release
```

Detects your versioning scheme from existing tags, computes the next version, shows you the tag, and asks for confirmation before pushing. On a fresh repo with no tags, it prompts you to choose CalVer or SemVer.

## Board workflow

The board commands add a lightweight project layer on top of the core workflow using GitHub Milestones and Issues. They are optional, the branch/commit/pr/ship workflow works the same with or without them.

**Create a milestone**

```sh
git clerk milestone new "Auth System" --scope auth
# Milestone #1 created.

git clerk milestone new "Auth System" "Handles login, registration, and SSO." --scope auth
# → with inline description

git clerk milestone new "Auth System" --scope auth -e
# → opens $EDITOR for the description
```

The `--scope` is used to derive branch names for all issues in this milestone. Every issue started under the milestone will live on a `type/scope` branch.

**Create issues**

```sh
git clerk issue new "Add login form" --type feat --milestone 1
git clerk issue new "Fix token expiry" --type fix --milestone 1
git clerk issue new "Write auth docs" --type docs --milestone 1
```

A type is required. A milestone is optional at creation time — an issue without one sits in the backlog. Both are required before `issue start` can be used.

**Start an issue**

```sh
git clerk issue start 1
# On branch 'feat/auth', active issue is #1.
#
# ## Description
# Login form with magic link.
```

Creates the branch from the milestone's scope (`feat/auth`), switches to it, records the active issue in local git config, and prints the issue body so you have the description and acceptance criteria in front of you as you begin. From here, the standard commit/PR/ship workflow applies.

**PR body gets `Closes #N` automatically**

Because `issue start` recorded the active issue, `git clerk pr` appends `Closes #1` to the PR body without any extra flags. The issue is closed on GitHub when the PR is squash-merged.

**Ship closes the milestone when all issues are done**

```sh
git clerk ship
```

Clears the active issue after merging. If the milestone has no remaining open issues, git-clerk closes it automatically and prints a confirmation.

**Other board commands**

```sh
git clerk board                          # session snapshot: active work + current milestone
git clerk milestone list                 # list open milestones with issue counts
git clerk milestone reopen 1             # reopen a closed milestone
git clerk issue list                     # list open issues, grouped by milestone
git clerk issue list --milestone 1       # filter to one milestone (flat list)
git clerk issue discard 3                # close an issue as not planned
```

## Commands

### `branch TYPE/scope`

Fetches the latest `origin/main` and creates a new branch from it.

```sh
git clerk branch feat/user-auth     # → feat/user-auth
git clerk branch fix/payment-api    # → fix/payment-api
git clerk branch chore/deps         # → chore/deps
```

The branch name is the only decision you make upfront. Every subsequent `commit` and `pr` command reads the type and scope from it — you never repeat yourself.

The fetch happens before branch creation, so you always start from the latest `main` regardless of how long ago you last pulled. If the branch already exists locally, git will error — delete it first or choose a different name.

### `commit DESCRIPTION [BODY]`

Creates a conventional commit by reading the type and scope from the current branch name. The commit message header is always `type(scope): description` — you only supply the description.

```sh
git clerk commit "add login form"
# → feat(user-auth): add login form
```

**Body**

By default there is no body — most commits don't need one. There are two ways to add one:

```sh
# Inline — pass the body as a second positional argument.
# Useful in scripts and LLM-driven workflows.
git clerk commit "add login form" "Supports email and SSO providers."

# Interactive — open $EDITOR. Save and exit to use the body; quit without
# saving to abort.
git clerk commit -e "add login form"
```

An empty string passed as BODY is treated the same as no body — only a non-empty string is included in the commit.

**Options**

| Flag | Description |
|------|-------------|
| `-A` | Stage all changes (`git add -A`) before committing |
| `-P` | Push to origin after committing (combine as `-AP`) |
| `-e` | Open `$EDITOR` to write the commit body interactively |
| `-t TYPE` | Override the type inferred from the branch name |
| `-s SCOPE` | Override the scope inferred from the branch name |

The `-t` and `-s` overrides are for cases where the commit type or scope differs from the branch — for example, bumping a lockfile on a `feat` branch:

```sh
git clerk commit -t chore "update lockfile"    # chore(user-auth): update lockfile
git clerk commit -s auth-core "fix token TTL"  # feat(auth-core): fix token TTL
```

`-P` pushes after committing, handy for follow-up commits once a PR is already open. It prints a reminder to refresh the PR description, since new commits may change the PR's scope.

### `pr TITLE [BODY]`

Pushes the current branch to origin (with upstream tracking), creates a GitHub PR against `main` with a conventional title derived from the branch name, prints the PR URL, then watches CI checks until they complete.

The PR title is constructed the same way as a commit header: `type(scope): title`. You supply only the human-readable title. Pass `--breaking` to mark a breaking change — it appends `!` to give `type(scope)!: title`, the conventional-commits marker. Because `ship` squash-merges the PR title onto `main`, this is where the breaking marker is recorded in history.

**Body**

By default no body is added. There are two ways to add one:

```sh
# Inline — pass the body as a second positional argument.
# Useful in scripts and LLM-driven workflows.
git clerk pr "Add login form" "Adds email/password and SSO login. Closes #42."

# Interactive — open $EDITOR. Save and exit to use the body;
# quit without saving to abort.
git clerk pr -e "Add login form"
```

An empty string passed as BODY is treated the same as no body.

**Options**

| Flag | Description |
|------|-------------|
| `-e` | Open `$EDITOR` to write the PR body interactively |
| `-t TYPE` | Override the type in the PR title |
| `-s SCOPE` | Override the scope in the PR title |
| `--breaking` | Append `!` to `type(scope)` to mark a breaking change |

The PR URL is printed to stdout as soon as the PR is created, before CI checks begin — you can share it while checks are still running. If checks fail, the run ends with a non-zero exit code.

If `issue start` was used to begin work on the current branch, `pr` automatically appends `Closes #N` to the PR body so the linked issue is closed when the PR merges.

### `ship`

Squash-merges the current branch's PR and brings your local environment back to a clean state on `main`. Must be run from the feature branch, not from `main`.

```sh
git clerk ship
```

Displays the PR title and number, asks for confirmation, then executes in order:

1. Squash-merges the PR into `main`
2. Deletes the remote branch
3. Switches to local `main`
4. Pulls latest from `origin/main`
5. Force-deletes the local branch

You end up on a clean, up-to-date `main` in one step.

If the branch was started with `issue start`, `ship` also clears the active issue from local git config. If the linked issue's milestone has no remaining open issues after the merge, the milestone is closed automatically.

**Options**

| Flag | Description |
|------|-------------|
| `-y` / `--yes` | Skip the confirmation prompt |
| `-u BRANCH` | After shipping, switch to BRANCH and merge `origin/main` into it |

`-u` is for cases where you paused work on one branch to ship a dependency first:

```sh
# Shipping fix/tech-debt while feat/user-auth is parked
git clerk ship -u feat/user-auth
# → ships fix/tech-debt, then switches to feat/user-auth and merges origin/main
```

`-y` is useful in automated contexts where you want to ship without interactive confirmation:

```sh
git clerk ship -y
```

### `watch`

Re-attaches to CI checks for the current branch's PR. Useful when you want to check in on CI after navigating away from the terminal during a `pr` run.

```sh
git clerk watch
```

### `board`

Prints a session snapshot: the current branch and active issue, the milestone in focus with its open issues expanded, and the remaining open milestones as one-line counts. The focused milestone is the active issue's milestone, or the first open milestone when no issue is active.

```sh
git clerk board
# Current branch: feat/foundation
# Active issue: #4 Auth
#
# #1  Foundation — 3 issues open, 2 closed
#   #3  chore  Full data model — schema and migrations
#   #4  feat   Auth — magic link login, session, protected routes
#
# #2  Portfolio — 2 issues open
```

### `milestone new TITLE [DESCRIPTION]`

Creates a GitHub Milestone. The `--scope` option is required and determines the branch name prefix used by all issues in this milestone.

```sh
git clerk milestone new "Auth System" --scope auth
git clerk milestone new "Auth System" "Handles login and SSO." --scope auth
git clerk milestone new "Auth System" --scope auth -e    # opens $EDITOR
```

**Options**

| Flag | Description |
|------|-------------|
| `--scope SCOPE` | Branch scope for all issues in this milestone (required) |
| `-e` | Open `$EDITOR` for the description |

### `milestone list`

Lists open milestones with their open/closed issue counts, under a repo header.

```sh
git clerk milestone list
# renov milestones:
# #1  Foundation — 3 issues open, 2 closed
# #2  Portfolio — 2 issues open
```

The closed count is omitted when nothing is closed.

### `milestone reopen NUMBER`

Reopens a closed milestone.

```sh
git clerk milestone reopen 1
```

### `issue new TITLE [BODY]`

Creates a GitHub Issue. `--type` is required. `--milestone` is optional — an issue without one sits in the backlog. Both are required before `issue start` can be used. Type labels are created in the repository automatically on first use.

```sh
git clerk issue new "Add login form" --type feat
git clerk issue new "Add login form" --type feat --milestone 1
git clerk issue new "Add login form" --type feat --milestone 1 -e
```

**Options**

| Flag | Description |
|------|-------------|
| `--type TYPE` | Conventional commit type label (required) |
| `--milestone NUMBER` | Milestone number |
| `-e` | Open `$EDITOR` for the issue body |

### `issue list`

Lists open issues grouped by milestone. With `--milestone`, lists just that milestone's issues as a flat list.

```sh
git clerk issue list
# #1 Foundation
#   #3  chore  Full data model — schema and migrations
#   #4  feat   Auth — magic link login, session, protected routes
#
# #2 Portfolio
#   #6  feat   Portfolio

git clerk issue list --milestone 1
# #3  chore  Full data model — schema and migrations
# #4  feat   Auth — magic link login, session, protected routes
```

Issues with no milestone are grouped last under `No milestone`.

### `issue start NUMBER`

Starts work on an issue: creates the branch from the milestone's scope, switches to it, records the active issue in local git config, and prints the issue body. Requires the issue to have a type label and be assigned to a milestone.

```sh
git clerk issue start 1
# On branch 'feat/auth', active issue is #1.
#
# ## Description
# Login form with magic link.
```

The issue body is printed so the description and acceptance criteria are in front of you as you start. The recorded active issue is used by `pr` (to append `Closes #N`) and cleared by `ship` (after merging).

### `issue discard NUMBER`

Closes an issue as "not planned".

```sh
git clerk issue discard 3
```

### `release`

Tags the current tip of `origin/main` and pushes the tag. Supports CalVer and SemVer.

git-clerk fetches the latest tags, computes the next version, shows you what it's about to create, and asks for confirmation before pushing anything.

```sh
git clerk release                      # auto-detect scheme, prompt for bump if SemVer
git clerk release --semver --bump minor
git clerk release --semver --bump major
git clerk release --calver
```

**Scheme detection**

If the repository already has version tags, git-clerk detects the scheme automatically — `--calver` and `--semver` are not needed. If no tags exist yet, git-clerk prompts you to choose interactively. Pass `--calver` or `--semver` to skip the prompt.

If both CalVer and SemVer tags are found (e.g. after a scheme migration), git-clerk exits with an error. Pass `--calver` or `--semver` explicitly to proceed.

**Options**

| Flag | Description |
|------|-------------|
| `--calver` | Use calendar versioning |
| `--semver` | Use semantic versioning |
| `--bump patch\|minor\|major` | SemVer component to increment; prompted if not provided (ignored for CalVer) |
| `-y` / `--yes` | Skip the confirmation prompt |

## Versioning schemes

### CalVer — `vYYYY.MM.N`

Tags are tied to the calendar month, with a sequential counter that resets each month:

```
v2026.06.1
v2026.06.2
v2026.07.1   ← new month, counter resets
```

Good fit for projects that ship continuously and want version numbers that communicate when something was released.

### SemVer — `vMAJOR.MINOR.PATCH`

Standard semantic versioning. The first tag on a repo with no prior tags starts at `v0.1.0`.

```
v0.1.0 → v0.1.1   (patch)
v0.1.1 → v0.2.0   (minor)
v0.2.0 → v1.0.0   (major)
```

The tag is always placed on `origin/main`, so run `release` after shipping all PRs for the version.

## Branch naming

All commands that read from the branch name (`commit`, `pr`) expect the format `type/scope`:

```
feat/user-auth
fix/payment-timeout
chore/upgrade-deps
docs/api-reference
```

The type must be one of the standard conventional commit types: `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`. The scope must start with a letter or digit and may contain letters, digits, hyphens, and underscores — spaces and special characters are not allowed. Both are validated by `branch` before the branch is created, and by `commit` and `pr` when reading the current branch name.

## License

MIT
