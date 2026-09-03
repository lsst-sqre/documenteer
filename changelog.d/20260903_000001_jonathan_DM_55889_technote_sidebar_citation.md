### New features

- A technote that sets `[technote] doi` in `technote.toml` now shows a **Cite** section in its sidebar: the DOI written as a full, resolvable `https://doi.org/…` hyperlink, and the technote's BibTeX entry behind a disclosure with a button that copies it to the clipboard. DataCite asks a DOI's landing page to display the DOI as a resolvable link alongside a bibliographic record, and this is where a technote says so.

  The entry is a BibTeX `techreport` composed at build time from the technote's own metadata — its authors, its publisher as the `institution`, its handle (`SQR-000`) as the `number`, its DOI, and its canonical URL — by the same `documenteer.citations` composer a user guide's citations use, so the two read identically. The entry is rendered into the page rather than fetched, so it stays selectable and copyable on a page whose JavaScript never runs.

  A technote that declares no DOI renders no Cite section at all and ships no script, so it builds exactly as it did before.

### Other changes

- Removed two technote template overrides, `sections/header-article.html` and `sections/sidebar-primary.html`, that named templates the technote theme no longer includes. Nothing about a rendered technote changes: the theme composes its article header and its sidebar from `sections/article-header.html` and `sections/logo.html`, so these two files had been inert since that reorganization. The sidebar override is replaced by one at the theme's own name, which is how the new Cite section reaches the page.
