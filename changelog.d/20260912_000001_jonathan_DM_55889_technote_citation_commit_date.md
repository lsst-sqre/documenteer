### New features

- A technote's citation is dated by its `[technote] date_updated`: the date `technote.toml` declares, or, where it declares none, the date of the commit the technote is published from, which technote 0.12 resolves from the checked-out commit's committer date. Every dated surface on the page therefore states one reproducible date — the sidebar's "Updated" line, the `citation_publication_date` metadata tag, the JSON-LD block, the **Cite** section's BibTeX `year` and `month`, and the citation at the end of the article — and rebuilding an unchanged commit composes exactly the same citation. Declaring `date_updated` is how to pin the citation to a fixed date instead of letting it follow the latest commit.

  `documenteer technote sync-cff` deliberately does *not* follow the commit: it writes `date-released` from a declared `date_updated` only, so a checked-in `CITATION.cff` does not go stale on every content commit, and a file with no `date-released` is valid CFF 1.2.0.
