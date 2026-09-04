### Backwards-incompatible changes

- `documenteer technote sync-cff` and `documenteer technote lint` now read the technote's document by building it with Sphinx, so both require the `technote` extra (`pip install documenteer[technote]`). The build uses the `dummy` builder, runs quietly into a temporary directory that is removed afterwards, forces the bibliography cache and intersphinx inventories off so it stays offline, and happens once per run. A technote Sphinx cannot read is reported — as a `sync-cff` error, or as the lint's TN203 — carrying Sphinx's own message instead of a traceback.

- The `technote-sync-cff` pre-commit hook is removed, along with `.pre-commit-hooks.yaml`. `documenteer technote sync-cff --check` is the supported way to keep `CITATION.cff` current: run it in CI, where the technote is built anyway. Rubin's shared technote workflow runs it for you.

### New features

- `documenteer technote sync-cff` now titles `CITATION.cff` with the technote's own top-level heading when `technote.toml` declares no `title` — which is the normal case, since `documenteer technote migrate` never writes one. Previously such a technote was cited by its series handle ("SQR-000") with a warning, while the published page carried the real title in `citation_title`, `DC.title`, and its JSON-LD. Everything else is still read from `technote.toml`, the release date included, so generation stays deterministic and a technote that declares a `title` generates exactly the file it generated before.

- The lint's TN105 DataCite cross-check and TN106 `CITATION.cff` comparison use that same resolved title, so a technote titled by its H1 is now cross-checked rather than skipped, and its `CITATION.cff` is no longer reported as permanently stale.

- The abstract rules (TN201/TN202/TN203/TN204) read the parsed document rather than scanning the source with Documenteer's own reStructuredText and Markdown heading scanners, which are deleted. An abstract found this way is the one the page publishes: an abstract pulled in with `include` is found however deeply the includes nest and wherever the included file lives, and a finding's `file:line:` prefix names the file the markup is actually written in. TN203 changes meaning from "the content file is valid JSON" to "Sphinx can read the document", which is a superset of it.
