### Bug fixes

- Fixed the rendering of Astrophysics Source Code Library (ASCL) references in bibliographies. The style rewrote the entry's `eid` field while formatting it, so any subsequent formatting pass fell through to the default template and rendered the record's `eprint` identifier as an arXiv link (for example `arXiv:1108.003` instead of `ascl:1108.003`). ASCL identifiers are now formatted without modifying the entry, and an `eprint` is only linked to arXiv when its `archivePrefix` says it belongs there, so ASCL records link to ascl.net for every entry type.
