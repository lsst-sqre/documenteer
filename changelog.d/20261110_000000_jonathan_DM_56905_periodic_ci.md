### Bug fixes

- `documenteer technote add-author` and `documenteer technote sync-authors` no longer write an empty `affiliations = []` key into the `[[technote.authors]]` table of an author who has no affiliations. Documenteer added an empty array of tables for every author it touched, which tomlkit 0.15.1 and earlier left out of the file but tomlkit 0.15.2 serializes, so a sync of an otherwise healthy `technote.toml` stopped being a byte-for-byte no-op.

### Other changes

- The `test`, `typing`, and `demo` nox sessions for the Sphinx development branch now skip themselves on Python 3.12, and the weekly Periodic CI matrix excludes that cell. Sphinx's main branch (9.3.0 development) requires Python 3.13 or later, so it can no longer be installed there. Sphinx 8 and 9 are still tested on Python 3.12. The Periodic CI test matrix also no longer cancels its remaining cells when one fails.

- The `test`, `typing`, and `demo` nox sessions now resolve sphinx-autodoc-typehints together with the Sphinx version they install. The release pinned in `uv.lock` is resolved for Sphinx 9 and, from 3.14, imports Sphinx internals that Sphinx 8 doesn't have, so the Sphinx 8 sessions now get the sphinx-autodoc-typehints release that supports Sphinx 8, as a Sphinx 8 user would.
