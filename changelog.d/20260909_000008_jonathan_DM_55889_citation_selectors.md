### New features

- A user guide's `citation-card` directive and `doi` role now select an entry three ways: by its `label`, by its `bibtex_key`, or by its DOI in any spelling (bare, `doi:`-prefixed, or as a `https://doi.org/` URL). `.. citation-card:: dp2`, `.. citation-card:: RTN-115`, and `.. citation-card:: 10.71929/rubin/3382540` all reach an entry, as do the same three forms as a role target — including with explicit-title syntax, ``:doi:`TAP <10.71929/rubin/3382540>` ``.

  This frees `label` to be what it reads as: the heading shown on the card and in the footer. A site with a registered landing page per data product can now write `label = "TAP"` on all forty of its TAP entries and select each of them by key or DOI, instead of stretching every label into a site-unique `"Object catalog (TAP)"`.

### Bug fixes

- Two `[[project.citations]]` entries carrying the same `label` no longer resolve silently to whichever was declared first. A selector several entries answer to now emits a `documenteer.citation_card` warning naming each candidate by its BibTeX key and asking the page to select by key or DOI; the card renders nothing and the role renders plain text, as they already did for a selector that resolves to nothing. No precedence is defined between the three kinds of selector, so a label never quietly beats a key.

### Other changes

- The warning for a selector no citation answers to no longer lists every label the site declares — already a 300-character line on a site with eleven entries. It now names at most three candidates as `key (label)`, counts the rest, and answers a near miss with the entry it resembles.

- A build warning about a citation whose `label` is shared with another entry now appends that entry's BibTeX key (`'TAP' (10.71929/rubin/3382540)`), so the `documenteer.citation_date`, `documenteer.citation_page`, and `documenteer.citation_card` reports say which entry they are about. An entry whose label is unique is still named by its label alone.
