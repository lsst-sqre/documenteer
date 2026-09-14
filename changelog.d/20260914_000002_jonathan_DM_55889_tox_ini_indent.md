### Other changes

- The `tox.ini` template that `documenteer technote update` writes now indents every `commands` and `deps` block with four spaces. The `html`, `linkcheck`, and `lint` environments used three, so a refresh propagated that mix into every technote and, on a technote whose file already used one width, produced whitespace-only hunks alongside the real change. An otherwise up-to-date technote reports `tox.ini: updated` once after this release.

- `docs/technotes/update.rst` now says plainly that the seven tooling files are replaced from the templates in full rather than merged, points at `--ignore-file` as the way to keep a file you have customized, and warns that `Makefile` and `tox.ini` must be held back together — a retained `tox.ini` may not define the `technote-lint` environment a refreshed `Makefile` calls.
