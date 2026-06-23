# Releasing

git-acta publishes SemVer-tagged releases to PyPI. Pushing a `v*.*.*` tag fires the publish workflow. Git tags are the source of truth for the version; `pyproject.toml` mirrors the latest tag.

## Release script

Once ready to tag a new release, run
```sh
uv run scripts/release.py            # version derived from the commits since the last tag
uv run scripts/release.py --stable   # one-time promotion of a 0.x project to v1.0.0
```
