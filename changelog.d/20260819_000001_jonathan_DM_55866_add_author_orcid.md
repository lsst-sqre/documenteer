### New features

- `documenteer technote add-author` accepts an `--orcid` option alongside `-a/--author-id`, so you can add an author you know by ORCID without first hunting down their key in `authordb.yaml`. ORCID is globally unique and author-supplied, so the lookup is exact rather than a name match; the ORCID can be bare or written as an `https://orcid.org/` URL. Exactly one of the two options identifies the author: passing both is a usage error, and passing neither still prompts for an author ID, so the interactive path is unchanged for anyone not using ORCIDs.

### Bug fixes

- `documenteer technote add-author` now reports an author it cannot find, and an author database it cannot reach, as a plain error message and exits 1, rather than printing a traceback. Previously an author ID with no entry in the Rubin author database, or a network failure or server error reaching the database, escaped as an unhandled exception.
