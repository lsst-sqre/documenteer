### New features

- `documenteer technote lint` now checks a technote's `CITATION.cff` with a new offline rule, **TN106**, which reports a file that no longer matches what `technote.toml` generates. It uses the same comparison `documenteer technote sync-cff --check` runs, so the linter and that CI gate can never disagree; a repository with no `CITATION.cff` is silent, because adopting the file is opt-in. The rule has a landing page under [the lint rule reference](https://documenteer.lsst.io/technotes/lint/).
