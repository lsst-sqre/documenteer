### Bug fixes

- The "Edit on GitHub" button now links to the correct file. The in-repository path is resolved from the Sphinx **source** directory rather than the directory containing `conf.py`, so projects that build with `sphinx-build -c . docs _build/html` (where those two directories differ) no longer produce links that 404. Projects whose source directory is the repository root also no longer get a stray `./` in the URL. This path is computed by a new `documenteer.ext.githubeditlink` extension, which the user-guide preset enables automatically.

- Building a user guide outside a Git checkout — from an sdist, or in a Docker image built without the `.git` directory — no longer fails with `InvalidGitRepositoryError`. The "Edit on GitHub" button is omitted instead, and the build proceeds. Setting `show_github_edit_link = false` is no longer needed to work around this.
