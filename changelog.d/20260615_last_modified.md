### New features

- User guide pages now show a "Last updated on <date>." timestamp at the bottom of each page, derived from the page's Git commit history. The date is the most recent commit across the page's own source file and any files it pulls in via `include`/`literalinclude`, so editing an included snippet updates every page that uses it. This is on by default and can be disabled with `show_last_updated = false` in the `[sphinx.theme]` table of `documenteer.toml`.

  The extension is also the single source of truth for the page's last-modified date in the HTML `<head>`: it emits the same Git date as an `article:modified_time` (Open Graph), `dcterms.modified` (Dublin Core), and a Schema.org `dateModified` (JSON-LD). The user-guide preset sets `git_last_updated_metatags = false` so the auto-loaded `sphinx-last-updated-by-git` extension (still used for the sitemap) doesn't emit a duplicate Open Graph tag from a separate Git computation.

  Because the date comes from Git, CI builds must check out the full history (set `fetch-depth: 0` with `actions/checkout`). To avoid publishing misleading dates, Documenteer detects a shallow clone, omits the timestamp from every page, and emits a build warning.
