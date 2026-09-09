### New features

- New `[project.citation_defaults]` table in `documenteer.toml` states once the bibliographic fields a user guide's `[[project.citations]]` entries share. It accepts `type`, `publisher`, `date`, `authors`, and `version` — the five fields several works can genuinely have in common — and every entry that states none of its own takes them. A site that mints a DOI per data product now writes each product as the four fields that tell it from the next (`doi`, `label`, `page`, `title`) instead of repeating the same publisher, author, year, and type on all forty of them.

  A field resolves from the first source that states it: the entry itself, then the `CITATION.cff` file the entry names, then the defaults table. A default therefore never overwrites a real value — a file's `date-released` beats a site-wide `date`, so a paper keeps its own year — and `authors` is all-or-nothing, an entry that names any author replacing the default list rather than extending it. A defaulted `date` counts as a date for the `documenteer.citation_date` warning, and a defaulted `version` beats the `project.version` a software entry describing this site's own package would otherwise inherit. Nothing about what a site publishes changes: the defaulted form of a set of entries produces exactly the metadata the fully-spelled form does.

  The table accepts only those five keys. Identity and presentation are per work — a DOI, a URL, a title, a label, a page, a note, a BibTeX key, `self`, `preferred`, `in_footer`, `cff`, and `cff_preferred` each name one work — so writing any of them, or misspelling a key the table does accept, fails the build with a message naming the table and the key.

### Other changes

- A `documenteer.toml` error about a key a table does not accept now names the key and lists the keys the table does accept, rather than reporting "extra inputs are not permitted" against the table as a whole.
