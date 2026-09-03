### New features

- A technote that sets `[technote] doi` in `technote.toml` now ends its article with a **Citing this document** section: the complete bibliographic citation — creators, year, title, publisher — with the DOI written as a resolvable `https://doi.org/…` hyperlink. DataCite asks a DOI's landing page to show a full citation a reader can copy, not just the identifier, and this is the sentence they copy into a bibliography.

  The citation is composed at build time from the technote's own metadata by the same `documenteer.citations` composer the sidebar's **Cite** section and a user guide's citations use, so no two surfaces on a technote can disagree, and none of them can disagree with the page they sit on.

  A technote that declares no DOI renders no section at all: the article footer stays as empty as the technote theme leaves it.
