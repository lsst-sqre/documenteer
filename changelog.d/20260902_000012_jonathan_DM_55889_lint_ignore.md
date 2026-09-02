### New features

- `documenteer technote lint` can now switch a rule off for one technote. List its code in the new `[technote.lint] ignore` array in `technote.toml`, or pass `--ignore CODE` (repeatable, and additive with the file's list). This is for a finding a technote can never act on — the standing case is **TN105** on a technote whose DOI was minted by the Zenodo–GitHub integration rather than by Rubin, where the registered title and creators cannot be corrected by anyone at Rubin, so the warning is permanent and `--strict` is out of reach forever.

  An ignored rule does not run at all: TN105 makes no DataCite request and TN101–TN103 make no author-database request when they are ignored, so a switched-off network rule costs nothing. Ignored rules are counted apart from errors and warnings and never affect the exit code, and the lint summary names each one with where it was configured (`Ignored 1 rule: TN105 (technote.toml [technote.lint]).`) so that CI output shows a rule is *off* rather than passing.

  The configuration is read from `technote.toml`'s own text rather than through technote's parsed model, so a technote can ignore a rule that is reporting on the very metadata that fails schema validation. The table is named for the thing it configures rather than the tool that reads it: the linter is expected to move into the `technote` package, which will then own this table's schema.

- A new **TN007** lint rule reports an ignore list the linter cannot act on — a code no rule carries, an entry that is not a rule code, or an `ignore` written in the wrong shape — rather than letting a typo silently leave a rule running. The valid entries around it still apply. Codes are validated against the rule registry and matched without regard to case.

### Other changes

- Each lint rule now carries the URL of the page that documents it (`Check.docs_url`), which the report's "Learn more" footer links to, in place of a module-level base URL. Every rule Documenteer ships documents itself on documenteer.lsst.io exactly as before; a rule set that documents its rules elsewhere can now say so while keeping its codes.
