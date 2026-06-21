# Releasing

git-acta publishes SemVer-tagged releases to PyPI. Pushing a `v*.*.*` tag fires the publish workflow. Git tags are the source of truth for the version; `pyproject.toml` mirrors the latest tag.

## Workflow

```sh
acta branch type/scope
acta commit -A "description" "Context for why."
acta pr "PR title" "What changed and why."
acta ship -y
```

Descriptions are not optional, they keep the repo self-documenting.

## Release script

Once ready to tag a new release, run
```sh
uv run scripts/release.py            # version derived from the commits since the last tag
uv run scripts/release.py --stable   # one-time promotion of a 0.x project to v1.0.0
```
