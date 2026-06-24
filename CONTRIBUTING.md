# Contributing

git-acta is developed with itself — branches, commits, and PRs all go through `acta`.

## Workflow

### Baseline

```sh
acta branch type/scope
acta commit -A "Description" -b "Context for why."  # -A stages everything before committing
acta pr "PR title" -b "What changed and why."
acta ship -y
```

Descriptions are not optional, they keep the repo self-documenting. The PR title
and body are what land on `main` and feed the release notes. Commit bodies get
squashed away on merge, so skip them by default.

The branch type drives the release bump (`feat` → minor, `fix` → patch), so type
by *consumer* impact: only changes under `src/acta/` — the shipped package — earn
`feat` or `fix`. Changes to `scripts/`, `tests/`, `.github/` or *.md files must
never be typed as `feat` or `fix`.

### Variations

```sh
git add path/a path/b && acta commit "Title"  # stage selectively (-A stages everything)
acta commit -AP "Title"                       # stage all + commit + push (follow-up on an open PR)
acta commit -t chore "Title"                  # override the type inferred from the branch
```

## PR body template

Base PR bodies on this structure. The `## Breaking` section is optional — include
it only for breaking changes:

```markdown
One-line summary of the change.

## Changes
- What changed, point by point

## Why
The motivation and context behind the change.

## Breaking
What breaks and the step users must take. (Omit for non-breaking changes.)
```
