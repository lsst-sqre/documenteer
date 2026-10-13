### Other changes

- Documenteer now declares support for Python 3.15, and the `test`, `typing`, and `demo` nox sessions and the GitHub Actions matrix now cover Python 3.12 through 3.15.
- The canonical Python version for development is now declared in a `.python-version` file at the root of the repository. uv reads it for `uv sync` and `uv run`, the noxfile derives its default sessions from it, and the GitHub Actions workflows read it in place of the former `PYTHON_VERSION` workflow variable to pick the interpreter for the lint and docs jobs and to identify the matrix cell that uploads the demo technote builds.
