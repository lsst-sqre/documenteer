### Bug fixes

- A user guide's `in_footer = false` no longer removes the site's preferred citation from the site-wide JSON-LD block. The preferred entry is by definition the citation the site asks readers to use, which is what schema.org `citation` states, so it is described there whether or not the footer repeats it; `in_footer` now governs the metadata only for the *additional* entries, which still reach the block only when a surface displays them. A site whose one entry was preferred and kept out of the footer previously emitted no citation metadata at all.
