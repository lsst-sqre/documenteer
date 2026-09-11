### New features

- New `documenteer technote update` command, which brings a technote repository up to the current standard from whatever state it is in. A technote that still has a `metadata.yaml` is converted, exactly as `documenteer technote migrate` converted it. A technote that already has a `technote.toml` is instead refreshed: the seven standard tooling files (`.github/dependabot.yml`, `.github/workflows/ci.yaml`, `.pre-commit-config.yaml`, `.gitignore`, `Makefile`, `requirements.txt`, and `tox.ini`) are rewritten from Documenteer's current templates, built from the metadata `technote.toml` declares. Both paths end in the same state, and a second run reports every file unchanged.

  The technote's own writing is never touched in a refresh — `README.rst` and the content file are the author's — and so is `conf.py` the moment it holds any Sphinx configuration of its own; a `conf.py` holding nothing but Documenteer's generated import line is brought up to date. Every file is reported as `updated`, `unchanged`, or `skipped (--ignore-file)`. `--ignore-file` (repeatable) holds back a file the technote has customized on purpose, and `--check` writes nothing and exits non-zero when any file is out of date, so a fleet campaign can detect drift and a technote's CI can enforce it.

### Bug fixes

- `documenteer technote migrate` no longer crashes with a `FileNotFoundError` when run on a modern technote. It is now a deprecated alias for `documenteer technote update`: it prints a notice pointing at the new command, takes the same options, and behaves identically. Its `--help` is also repaired — `-d/--dir` is no longer labelled `[required]` when it has a default, and the orphaned sentence fragment about the Rubin author DB is gone.
