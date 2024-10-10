### Bug fixes

- Pin `sphinx` to < 8.1.0. [Sphinx 8.1.0](https://github.com/sphinx-doc/sphinx/compare/v8.0.2...v8.1.0) contains [a commit](https://github.com/sphinx-doc/sphinx/pull/12762/files#diff-a4c6bf1492ef480b94af82c988f64ca56fa256fab0ed043a5ad3d4043f89a645L14) that removes the `ExtensionError` export from the `sphinx.util` package. This currently breaks the [sphinxcontrib-mermaid](https://github.com/mgaitan/sphinxcontrib-mermaid) dependency.

