### Other changes

- `documenteer technote migrate` now writes a project that can run every command the technote documentation tells its author to run. The generated `requirements.txt` floor is raised to `documenteer[technote]>=2.5.0,<3` — the first release carrying `documenteer technote sync-cff` and the technote linter — and the generated `tox.ini` and `Makefile` gain a `sync-cff` environment and target beside `sync-authors`, so a migrated technote regenerates its `CITATION.cff` through its own tooling instead of a hand-installed Documenteer.
