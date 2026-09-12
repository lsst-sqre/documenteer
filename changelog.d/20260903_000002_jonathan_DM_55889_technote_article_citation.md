### New features

- Every technote now ends its article with a **Citing this document** section: the complete bibliographic citation — creators, year, title, publisher — ending in a resolvable hyperlink to the work, `https://doi.org/…` for a technote registered with a DOI and the technote's `canonical_url` for one without. DataCite asks a DOI's landing page to show a full citation a reader can copy, not just the identifier, and this is the sentence they copy into a bibliography.

  The citation is composed at build time from the technote's own metadata by the same `documenteer.citations` composer the sidebar's **Cite** section and a user guide's citations use, so no two surfaces on a technote can disagree, and none of them can disagree with the page they sit on.

  Displaying a citation is not claiming a registration, so nothing that needs a DOI is rendered without one: the sidebar's DOI line, the `citation_doi` Highwire tag, `DC.identifier` as a DOI, the JSON-LD `identifier`, and `documenteer technote lint`'s TN105 DataCite cross-check are all DOI-only, and a technote without one emits none of them. A technote that declares neither a `doi` nor a `canonical_url` has nothing to be located by, and its citation is the same reference ending after the publisher, with nothing hyperlinked and no `url` field in the entry.
