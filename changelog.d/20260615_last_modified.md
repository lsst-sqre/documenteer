### New features

- User guide pages now show a "Last updated on <date>." timestamp in the footer, derived from the page's Git commit history. The date is the most recent commit across the page's own source file and any files it pulls in via `include`/`literalinclude`, so editing an included snippet updates every page that uses it. This is on by default and can be disabled with `show_last_updated = false` in the `[sphinx.theme]` table of `documenteer.toml`.

  Because the date comes from Git, CI builds must check out the full history (set `fetch-depth: 0` with `actions/checkout`). To avoid publishing misleading dates, Documenteer detects a shallow clone, omits the timestamp from every page, and emits a build warning.
