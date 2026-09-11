### Other changes

- A technote project's `technote-lint` tox environment now runs `documenteer technote sync-cff --check` after `documenteer technote lint`, so `make lint` enforces `CITATION.cff` freshness with the same command the documentation tells authors to run in CI. Run `documenteer technote update` to pick up the new environment.

- Corrected the technote documentation's claim that Rubin's shared technote workflow runs the technote linter and the `CITATION.cff` freshness check. It does not: it runs the Pre-commit hooks, the build, and the upload. The pages now name the repository's own `make lint` / `tox run -e technote-lint` target as what enforces both, and point at [rubin-sphinx-technote-workflows#12](https://github.com/lsst-sqre/rubin-sphinx-technote-workflows/issues/12) as the pending step for the shared workflow.
