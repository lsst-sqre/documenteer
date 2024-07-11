# Change Log

<!-- scriv-insert-here -->

<a id='changelog-1.4.0'></a>
## 1.4.0 (2024-07-11)

### New features

- Update to technote 0.9.0. This new version of the technote theme features a two column layout that allows wide content, such as tables, code blocks, and figures, to span the full width of the page (bleeding beyond the text column).

<a id='changelog-1.3.0'></a>
## 1.3.0 (2024-05-03)

### New features

- Added a `[sphinx.redirects]` table to `documenteer.toml`. This provides support for configuring page redirects from the TOML configuratin. Redirects are useful if pages move because of a content re-organization. This feature is based on [sphinx-rediraffe](https://github.com/wpilibsuite/sphinxext-rediraffe).

- Added the [sphinxcontrib-youtube](https://sphinxcontrib-youtube.readthedocs.io/en/latest/index.html) for embedded YouTube and Vimeo videos into documentation pages. This extension is available for both user guides (`documenteer.conf.guide`) and technotes (`documenteer.conf.technotes`).

### Bug fixes

- Technotes ignore files in the repository with `.md`, `.rst`, and `.ipynb` extensions if they aren't the index file. Since technotes are single-page documents, only the index file should be used as a source file. This change lets authors include auxiliary notebooks with their technotes without having to explicitly exclude them from the technote build process. This is implemented with `technote.conf.extend_excludes_for_non_index_source`.

- In `documenteer.ext.lssttasks`, attempt to import `_pseudo_parse_arglist` from `sphinx.domains.python._annotations` before falling back to the `sphinx.domains.python` module. Ultimately this is a workaround.

- Fix setting the rebuild condition for the `documenteer.ext.githubbibcache` extension.

- Fixed the monospace text baseline alignment issue in Safari for technotes by updating to technote 0.8.0. In this version, the font size of the code is set to be 0.9em so that the browser doesn't push the text below the baseline in case its larger than the Source Sans body text. This version also changes the font size on the html element to 100% and instead increases the baseline body text size to 1.1rem on the body element. This change should help technotes respect the user's browser font size settings while also making the rem unit work as expected.

### Other changes

- Added `defusedxml` as a dev dependency. This is used by Sphinx's `sphinx.testing.fixtures`, but isn't included as a dependency by Sphinx itself. This change ensures that `defusedxml` is installed when running the tests.

<a id='changelog-1.2.2'></a>
## 1.2.2 (2024-04-11)

### Bug fixes

- Update `jira_uri_template` configuration default to `https://rubinobs.atlassian.net/browse/{issue}`. This will make all :jira:, :jirab:, and :jirap: roles point to the new Jira instance for Rubin Observatory.
- Drop `jira.lsstcorp.org` from the linkcheck ignore list defaults for `documenteer.config.guide` since that instance is no longer being used.
- Replace `jira.lsstcorp.org` URLs in documentation to `rubinobs.atlassian.net`.

<a id='changelog-1.2.1'></a>
## 1.2.1 (2024-04-02)

### Bug fixes

- Fix the "Source parser for markdown not registered" error for Markdown-based technotes. With the MyST-NB extension the Markdown parser is automatically registered, so the `documenteer.conf.technote` configuration now resets the `source_suffix` configuration originally created by the Technote package.

<a id='changelog-1.2.0'></a>
## 1.2.0 (2024-03-26)

### New features

- Rubin user guides (`documenteer.conf.guide`) and technotes (`documenteer.conf.technote`) now include [MyST-NB](https://myst-nb.readthedocs.io/en/latest/) to support Jupyter Notebooks in Sphinx documentation. The MyST-NB extension also supersedes MyST-Parser for Markdown syntax support. For guides, Jupyter Notebook files can be intermixed with Markdown (`.md`) and reStructuredText (`.rst`) files. An `ipynb` file is considered as a page in the documentation. For technotes, the Jupyter Notebook must be named `index.ipynb`. By default, these configurations use MyST-NB's "auto" mode for notebook execution: only if a notebook is missing outputs will it be executed.

<a id='changelog-1.1.1'></a>
## 1.1.1 (2024-02-21)

### Bug fixes

- `setuptools` is now included in the core package dependencies. The `documenteer.ext.bibtex` extension uses `pybtex`, which is turn uses `pkg_resources` from `setuptools`. In Python 3.12, setuptools is not available in Python environments by default. This direct dependency can be removed once `pybtex` is updated to use `importlib.metadata`.

### Other changes

- Update to the Python project configuration guide for `documenteer.toml` to use an example project other than "Documenteer" in the examples. Also emphasize the requirement that the project must be installed to use the `[project.python]` configuration in `documenteer.toml`.

<a id='changelog-1.1.0'></a>
## 1.1.0 (2024-01-30)

### New features

- Update to Technote 0.7.0.
- Add `sphinx_design` as a default extension for technotes.

### Bug fixes

- If the `version` field in `documenteer.toml` isn't set, and the project isn't a Python package, then the default value is now "Latest." The former default, None, was invalid.

<a id='changelog-1.0.1'></a>
## 1.0.1 (2024-01-02)

### Bug fixes

- In `documenteer technote migrate`, change the icon for a file deletion event from ❌ to 🗑️.

### Other changes

- Update the migration docs around the migration tool and convert the previous manual migration docs into a reference of the file-by-file changes.

<a id='changelog-1.0.0'></a>
## 1.0.0 (2023-12-17)

### Backwards-incompatible changes

- Documenteer now requires Python 3.11 or later.

- Dependency changes:

  - Pydantic 2.0 or later.
  - Sphinx 7 and later (and docutils 0.20 and later)
  - pydata-sphinx-theme < 0.13 on account of a change in logo path checking (affects user guide projects).

- Dropped support for the original technote configuration for Documenteer < 1.0. The `documenteer.conf.technote` configuration now uses the modern platform build with [Technote](https://technote.lsst.io). See new features below for more details.

- Dropped CLI commands:

  - The `refresh-lsst-bib` CLI command is removed. Technotes now automatically vendor lsst-texmf's bib files and cache them using `documenteer.ext.githubbibcache`.
  - The `build-stack-docs` CLI command is removed and replaced by the `stack-docs` and `package-docs` CLIs in Documenteer 0.3.0.

- The `documenteer.conf.pipelines` and `documenteer.conf.pipelinespkg` configuration modules now derive from `documenteer.conf.guide`. In doing so, the Pipelines documentation configuration works the same as Rubin Guides, but with additional configuration for pipelines-specific Sphinx extensions and other configurations. With this change, the `lsst-sphinx-bootstrap-theme` is no longer used by Documenteer.

- The `documenteer.sphinxext` module has been removed and the existing Sphinx extensions within it are now available from `documenteer.ext`. It's no longer possible to use `documenteer.sphinxext` to automatically load all Documenteer Sphinx extensions. Extensions need to now be added individually to the `extensions` configuration variable in `conf.py`. The migrated extension modules are:

  - `documenteer.ext.bibtex`
  - `documenteer.ext.jira`
  - `documenteer.ext.lsstdocushare`
  - `documenteer.ext.lssttasks`
  - `documenteer.ext.mockcoderefs`
  - `documenteer.ext.packagetoctree`

### New features

- All-new technote configuration for Rubin Observatory. Technotes are now built with a framework we created by the same name, [Technote](https://technote.lsst.io). The new technotes feature a responsive design, better on-page navigation, and overall cleaner design that matches Rubin Observatory's visual identity. For authors, technotes use a new configuration file, `technote.toml`, which replaces `metadata.yaml`. Technotes can also be written in Markdown (in addition to continuing reStructuredText support) thanks to [MyST Parser](https://myst-parser.readthedocs.io/en/latest/intro.html). Other key features:

  - You can migrate your existing technote by running the `documenteer technote migrate` CLI command. The migration process is explained in detail at https://documenteer.lsst.io/technotes/migrate.html.

  - Rubin technotes automatically use the bib files from https://github.com/lsst/lsst-texmf. In your text, use the `:cite:` directive with a bibkey from those bib files to cite a reference. Documenteer automatically retrieves the bib files from GitHub so you no longer need to maintain a copy in your repository.

  - Rubin technotes include a richer metadata base than the original technote system. This will make it easier to cite technotes. Part of the richer metadata system is the authors table in `technote.toml` files. This author information is derived from, and synchronized with, the `authordb.yaml` file in [lsst/lsst-texmf](https://github.com/lsst/lsst-texmf). The `documenteer technote add-author` and `documenteer technote sync-authors` CLI commands can help you manage author information in your technote.

  - The title for a technote is now derived from the top-level heading in the content itself.

  - There is a new `abstract` directive for marking up a technote's abstract or summary. This replaces the use of a note for the summary. This summary abstract is used by the documentation crawler to build https://www.lsst.io.

  - Technotes can now indicate their status with the `technote.status` field in `technote.toml`. For example, a technote can start out as a draft. You can also mark a technote as deprecated and link to superseding websites.

  - The new technote configuration comes pre-loaded with extensions for making diagrams as code, including `sphinxcontrib-mermaid` and `sphinx-diagrams`.

- Improvements for Rubin user guides (`documenteer.conf.guide`):

  - Add `sphinx-jinja` to the Rubin guides configuration by default.
  - Add `sphinx-rediraffe` to the Rubin guides configuration by default.
  - Use [sphinxcontrib-jquery](https://github.com/sphinx-contrib/jquery/) to ensure jQuery is available for user guide and Pipelines documentation builds.
  - New `sphinx.exclude` field to `documenteer.toml` to list files for exclusion from a documentation project. More files and directories like `.venv` and `requirements.txt` are now excluded, as well.
  - New support for embedding OpenAPI documentation in a Redoc-generated subsite. The `documenteer.ext.openapi` extension can call a user-specified function to generate and install the OpenAPI specification the Sphinx source. For user guide projects, the `[project.openapi]` table in `documenteer.toml` can be used to configure both the `documenteer.ext.openapi` and `sphinxcontrib-redoc` extensions. [sphinxcontrib-redoc](https://sphinxcontrib-redoc.readthedocs.io/en/stable/) is installed and configured by default for all Rubin user guide projects (projects that use `documenteer.conf.guide`).

- A new extension, `documenteer.ext.githubbibcache`, can fetch and locally cache BibTeX files from one or more public GitHub repositories. These bibfiles are automatically added to `sphinxcontrib-bibtex`'s `bibtex_files` configuration. This powers the technote's automatic use of bib files from the https://github.com/lsst/lsst-texmf repository.

### Bug fixes

- `Retry` is now imported directly from `urllib3` instead of the vendored version in requests.

### Other changes

- Adopted Scriv for maintaining the change log.

## 0.8.4 (2023-07-28)

Fixes:

- Pin Sphinx < 7 for the `guide` extra (same as the pinning already being done for the `pipelines` and `technote` extras).

## 0.8.3 (2023-07-03)

Fixes:

- Pin Pydantic < 2.0.0. This is a temporary measure while we add and test compatibility with Pydantic 1 and 2.

## 0.8.2 (2023-06-27)

Fixes:

- Fixed a bug in the `help` subcommand for the `package-docs` and `stack-docs` commands.

## 0.8.1 (2023-06-27)

Fixes:

- Fixed a bug in the in the `help` subcommand for the `package-docs` and `stack-docs` commands.

## 0.8.0 (2023-06-23)

New features:

- Added a `-W` / `--warning-is-error` flag to the `package-docs build` and `stack-docs build` commands for Science Pipelines documentation builds. This flag causes Sphinx to treat warnings as errors, which is useful for CI builds.
- Also added a `-n` / `--nitpicky` flag that enables Sphinx's nitpicky mode to flag warnings when links cannot resolve.

Fixes:

- Pinned `sphinx-autodoc-typehints<1.23.0` to avoid a Sphinx version conflict with `sphinx-design`. The former required Sphinx >= 7.

## 0.7.5 (2023-06-07)

Fixes:

- Use [sphinxcontrib-jquery](https://github.com/sphinx-contrib/jquery/) to ensure jQuery is available for user guide and Pipelines documentation builds. Sphinx 6 dropped jQuery from its default theme, and the new pydata-sphinx-theme v0.12 does not include it either.

## 0.7.4 (2023-05-16)

Fixes:

- Pinned Sphinx < 7 for the `pipelines` and `technote` extras since their themes are not currently compatible with Sphinx 7 and later.

## 0.7.3 (2023-03-20)

Fixes:

- Add `requirements.txt` and `.venv`/`venv` to the default `exclude_patterns` for User Guides.

## 0.7.2 (2023-03-01)

Fixes:

- Temporarily pin pydata-sphinx-theme to <0.13. The new version changed how it treats light/dark logos.

## 0.7.1 (2023-02-23)

Fixes:

- Temporarily pinning Mermaid to 9.4.0 in the User Guide configuration to workaround a change in the Mermaid CDN.

## 0.7.0 (2022-10-20)

- Documenteer provides a new Sphinx configuration profile for general Rubin user guide projects, `documenteer.conf.guide`.
  This configuration profile features the new [pydata-sphinx-theme](https://pydata-sphinx-theme.readthedocs.io/en/stable/), with customizations based on design tokens from the [Rubin Style Dictionary](https://style-dictionary.lsst.io).
  Most metadata and Sphinx configurations can also be set through a `documenteer.toml` file, located alongside the standard Sphinx `conf.py` file.
  Install `documenteer[guide]` with `pip` to get the dependencies needed for this Sphinx configuration.

- Packaging updates:

  - Documenteer now uses `pyproject.toml` for its packaging.
  - The GitHub Actions workflows now use SQuaRE composite workflows for many steps.
  - The README and change log are now written in Markdown.
  - Sphinx version 5 is now included in the test matrix.

## 0.6.13 (2022-07-29)

- Fixed the "Edit on GitHub" URL string construction in `documenteer.conf.technote`.

## 0.6.12 (2022-07-04)

- Add a `tstn` role for linking to Telescope and Site technical notes.

## 0.6.11 (2022-05-12)

Fixes:

- Fix type checking by adding stub packages.

Changes:

- Add new roles for linking to technical notes:

  - sitcomtn
  - rtn
  - pstn

- Link to technical notes, which are hosted on [lsst.io](https://www.lsst.io), now linking directly to [lsst.io](https://www.lsst.io) rather than going through `ls.st``. This includes the sqr, dmtn, etc. roles and all the new roles mentioned above.
- Use `importlib.metadata` for getting the package version, rather than `pkg_resources`.
- Move to a `src/` based package layout for consistency.

Issues:

- Temporarily disable testing the Doxygen-related Sphinx extensions.

## 0.6.10 (2022-03-09)

Fixes:

- Support sphinx-jinja 2.0.0 by using the `sphinx_jinja` extension name in `documenteer.conf.pipelines` and `documenteer.conf.pipelinespkg`.
  Installations that use sphinx-jinja < 2 will continue to use `sphinxcontrib.jinja` since the `sphinx-jinja` version is dynamically detected.

## 0.6.9 (2021-05-10)

Fixes:

- Add support for Sphinx 4.x by switching from `sphinx.util.inspect.Signature` to `sphinx.util.inspect.signature` for Sphinx versions 2.4 and later.
  A minimum Sphinx version 2.4 is now required.
- Updated testing matrix to test against the latest patch versions of Sphinx 2.x, 3.x, and 4.x.

## 0.6.8 (2021-05-10)

Fixes:

- Document conda-forge based installations.
- Stack documentation builds no longer include meta or build-related files in the HTML site output, such as:

  - `conf.py`
  - `.doctrees`
  - `doxygen.conf`
  - `manifest.yaml`
  - Build products from sconsUtils-based Doxygen builds, including `html` and `xml`.

## 0.6.7 (2021-04-26)

Fixes:

- The `html_extras_path` is no longer accidentally reset to `[""]` in `documenteer.conf.pipelines`.

- sphinx-automodapi introduces an autodoc enhancement that replace's autodoc's attr getter for `type` with a custom function.
  However, we're finding that this enhancement is incompatible with Pybind11 static properties that are part of the LSST Science Pipelines API.
  This release includes a new extension, `documenteer.ext.autodocreset`, that resets the attr getter for `type` to the one built into autodoc.
  This extension is used by default in `documenteer.config.pipelines` and `documenteer.config.pipelinespkg`.

## 0.6.6 (2021-02-17)

Fixes:

- Updated the `documenteer.conf.pipelines` (and `documenteer.conf.pipelinespkg`) configuration modules so that they no longer configure `doxylink` if the Doxygen tag file is not present.
  This change is useful for single-package documentation builds of pure-Python packages.

## 0.6.5 (2021-02-12)

Fixes:

- Updated intersphinx links for Numpy and Astropy in the Pipelines configuration (`documenteer.conf.pipelines` and `documenteer.conf.pipelinespkg`).

## 0.6.4 (2021-02-02)

Fixes:

- Fixed a syntax issue with the package's long description, and added a linting rule to prevent this issue in the future.

## 0.6.3 (2021-02-01)

Fixes:

- Documenteer works with the latest version of [sphinxcontrib-bibtex](https://github.com/mcmtroffaes/sphinxcontrib-bibtex).
  Both the new (`documenteer.conf.technote`) and old (`documenteer.sphinxconfig.technoteconf`) versions of the technote configuration use the new `bibtex_bibfiles` configuration variable.
  Version 2.0.0 or later of `sphinxcontrib-bibtex` is now required because of that package's API.

## 0.6.2 (2020-10-08)

Fixes:

- The `build-stack-docs` CLI (replaced by `stack-docs build`) now defaults to not generating a Doxygen configuration, or running Doxygen.
  This is consistent with the original behavior of `build-stack-docs`, which did not perform a Doxygen build.

- The `autocppapi` directive now works even if the corresponding Doxylink symbol map is unavailable.
  This feature is useful for any circumstance when a Doxygen subsite that is normally present is unavailable, such as for a single-package documentation build.

- The Doxygen subsite is only added to `html_extras_path` if the `_doxygen/html` directory is present.

- Remove the matplotlib plot extension from the legacy `documenteer.sphinxconf` configuration because the extension appears to be incompatible with Sphinx 3.x.

## 0.6.1 (2020-10-06)

Fixes:

- Removed the `breathe` extension from the deprecated `documenteer.sphinxconf` Sphinx configuration for Pipelines documentation.
  This is because documenteer no longer includes `breathe` in its dependencies.
  Though this is backwards incompatible, `breathe` was never used in production documentation.

## 0.6.0 (2020-10-01)

- Documenteer now works with Sphinx 2.0+.

- Documenteer's dependencies now cleanly map to each use case:

  - `pip install documenteer` installs _only_ the dependencies required to use Documenteer's own Sphinx extensions.
    The dependencies are not strictly pinned (aside from Sphinx >= 2.0).

  - `pip install documenteer[technote]` installs the core dependencies required by Documenteer, as well as the pinned Sphinx theme and extensions used by all technote projects.

  - `pip install documenteer[pipelines]` installs the core dependencies required by Documenteer, as well as the Sphinx theme and extensions used by pipelines.lsst.io.
    These extensions no longer have pinned versions.

  Development and test dependencies are no longer pinned.

- Python 3.6 is no longer officially supported.
  Documenteer is tested with Python 3.7 and 3.8.

- New Sphinx configuration facilities should prevent recursion issues by more cleanly populating the Python attributes in the configuration module:

  - Technote projects now import `documenteer.conf.technote` in their `conf.py` files.
  - Stack projects now import `documenteer.conf.pipelines` in their `conf.py` files.
  - Individual Stack packages now import `documenteer.conf.pipelinespkg` in their `conf.py` files.

  The previous configuration sub-package, `documenteer.sphinxconf` is deprecated.
  [[DM-20866](https://rubinobs.atlassian.net/browse/DM-20866)]

  Overall, the configurations are compatible with these exceptions:

  - ReStructuredText source files are no longer copied into the built site for Pipelines projects (`html_copy_source` is `False`).
    This change reduces the upload site of the pipelines.lsst.io site.
  - Updated the MathJax CDN URL to point to cdnjs.

- The stack documentation build (`stack-docs build`) can now run a Doxygen build to generate an HTML site and tag file of the C++ API.
  The HTML site is copied into the `cpp-api` directory of the Sphinx site, during the Sphinx build.
  This Doxygen build replaces, and is independent of, the Doxygen build tooling in [sconsUtils](https://github.com/lsst/sconsUtils), [lsstDoxygen](https://github.com/lsst/lsstDoxygen), and the [base](https://github.com/lsst/base) package.

  ReStructuredText content can now link into the embedded Doxygen-generate site using the [sphinxcontrib-doxylink](https://sphinxcontrib-doxylink.readthedocs.io/en/latest/) extension with the new `lsstcc` role.
  Authors can use a new command, `stack-docs listcc` to find available APIs for linking.

  There is a new directive, `autocppapi`, part of the `documenteer.ext.autocppapi` extension, that helps you list and link to C++ APIs in a namespace.
  It's intended to be used equivalently to the `automodapi` extension.

  The built-in Doxygen build considers all Stack packages with a `doc/doxygen.conf.in` file.
  Documenteer creates a Doxygen configuration from the contents of each package's `doxygen.conf.in` file, along with built-in defaults appropriate for pipelines.lsst.io.
  For example, individual packages can add to the `EXCLUDE` tag.
  By default, each package's `include` directory is included in the Doxygen build.

  [[DM-22698](https://rubinobs.atlassian.net/browse/DM-22698), [DM-23094](https://rubinobs.atlassian.net/browse/DM-23094), [DM-22461](https://rubinobs.atlassian.net/browse/DM-22461)]

- Improved Sphinx runner (`documenteer.sphinxrunner`).
  [[DM-26768](https://rubinobs.atlassian.net/browse/DM-26768)]

- Added static type checking using [mypy](https://mypy.readthedocs.io/en/stable/).
  [[DM-22717](https://rubinobs.atlassian.net/browse/DM-22717), [DM-26288](https://rubinobs.atlassian.net/browse/DM-26288)]

- Improved packaging, testing, and development environment:

  - PEP 518-ify the build process by adding a `pyproject.toml` file.
  - Removed the deprecated pytest-runner plugin.
  - Moved most of the packaging configuration to `setup.cfg`.
  - Adopted black and isort for code formatting.
  - Migrated to `tox` for running tests.
  - Migrated to `pre-commit` for running linters and code formatters.
  - Migrated to GitHub Actions from Travis CI.

  [`DM-22957 <https://rubinobs.atlassian.net/browse/DM-22957>`_, `DM-26288 <https://rubinobs.atlassian.net/browse/DM-26288>`_]

- Documentation improvements:

  - Added a new Developer guide and Release procedure guide.
  - Added an installation page.
  - Moved the Python API reference to its own page.
  - Improved the README to list features.

- Added GitHub community health features: contributing, support, and code of conduct files.

## 0.5.5 (2019-12-09)

- Technote configuration now uses `yaml.safe_load` instead of `yaml.load`.
  See the [pyyaml docs for details](https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation).
  [[DM-22537](https://rubinobs.atlassian.net/browse/DM-22537)]

## 0.5.4 (2019-11-03)

- This new version of the technote sphinx theme should fix the edition link in the sidebar for non-main editions.
  [[DM-20839](https://rubinobs.atlassian.net/browse/DM-20839)]

## 0.5.3 (2019-08-07)

- Enabled the `html_use_index` and `html_domain_indices` configurations for Stack documentation projects to enable automatic index generation.
  The `genindex` contains links to all command-line options and Python objects (Sphinx's domains).
  This also opens us up to a more general content index by way of the [index directive](https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#index-generating-markup).
  [[DM-20850](https://rubinobs.atlassian.net/browse/DM-20850)]

- Fixed compatibility with docutils 0.15.
  Now Sphinx will control which version of docutils is used, which should now be 0.15.

- Also updated the intersphinx URL for Pandas to use https.

## 0.5.2 (2019-08-01)

- Add [sphinxcontrib.autoprogram](https://sphinxcontrib-autoprogram.readthedocs.io/en/stable/) to enable automated reference documentation of argparse-based command-line scripts.
  This extension is available with the `documenteer[pipelines]` installation extra and enabled by default for LSST Science Pipelines projects.
  [[DM-20767](https://rubinobs.atlassian.net/browse/)]

- Update the official list of tested and supported Python versions to Python 3.6 and 3.7.

## 0.5.1 (2019-07-22)

- Pin docutils temporarily to `0.14`.
  The latest release, 0.15, is currently incompatible with the `:jira:` role.

## 0.5.0 (2019-02-11)

- The stack documentation build now requires that packages be explicitly required by the main documentation project's EUPS table file.
  Before, a package only needed a `doc/manifest.yaml` file and to be currently set up in the EUPS environment to be linked into the documentation build.
  This would lead to packages being included in a documentation build despite not being a part of that stack product.
  [[DM-17765](https://rubinobs.atlassian.net/browse/DM-17765)]

- This release adds the [sphinx-jinja](https://github.com/tardyp/sphinx-jinja) extension for `documenteer[pipelines]` installations.
  This extension makes it possible to dynamically create content with Jinja templating.

  The `documenteer.sphinxconfig.stackconf` module sets up a `default` context for the `jinja` directive that includes all module attributes in the Sphinx config module.

- The `documenteer.sphinxconfig.stackconf` module includes several new configuration attributes that are driven by the presence of an `EUPS_TAG` environment variable.
  The overall intent of these variables is to make it possible to render installation documentation for the https://pipelines.lsst.io documentation project from the `EUPS_TAG` environment variable.
  The variables are:

  - `release_eups_tag`
  - `release_git_ref`
  - `release`
  - `version`
  - `scipipe_conda_ref`
  - `newinstall_ref`
  - `pipelines_demo_ref`

  These variables are accessible from the `jinja` directive's context.
  [[DM-17065](https://rubinobs.atlassian.net/browse/DM-17065)]

- This release also added some new substitutions to the `rst_epilog` of stack-based projects:

  - `|eups-tag|` --- the current EUPS tag, based on the `EUPS_TAG` environment variable.
  - `|eups-tag-mono|` --- monospace typeface version of `|eups-tag|`.
  - `|eups-tag-bold|` --- bold typeface version of `|eups-tag|`.

  The `|current-release|` substitution is no longer available.

- Fixed some bugs with the display of copyrights in stack-based projects.

- The project's name is also used as the `logotext` at the top of the page for stack-based projects.
  Previously the `logotext` would always be "LSST Science Pipelines."
  [[DM-17263](https://rubinobs.atlassian.net/browse/DM-17263)]

- Added the following projects to the intersphinx inventory of stack-based projects:

  - `firefly_client`
  - `astro_metadata_translator`

## 0.4.5 (2019-02-06)

- Added a new `lso` role for linking to LSST Operations documents in DocuShare.

## 0.4.4 (2019-02-05)

- Updated scikit-learn's intersphinx inventory URL (now available as HTTPS) in the `documenteer.sphinxconfig.stackconf`.
- Fixed the `lsst-task-config-subtasks` directive so that it can introspect items in an `lsst.pex.config` `Registry` that are wrapped by a `ConfigurableWrapper`. [(DM-17661)[https://rubinobs.atlassian.net/browse/DM-17661]]

## 0.4.3 (2018-11-30)

- Pin [sphinxcontrib-bibtex](https://github.com/mcmtroffaes/sphinxcontrib-bibtex) to version 0.4.0 since later versions are incompatible with Sphinx <1.8.0.
  [[DM-16651](https://rubinobs.atlassian.net/browse/DM-16651)]

## 0.4.2 (2018-11-01)

- Handle cases where an object does not have a docstring in `documenteer.sphinxext.lssttasks.taskutils.get_docstring`.
  This improves the reliability of the `lsst-task-api-summary` directive.
  See (DM-16102)(https://rubinobs.atlassian.net/browse/DM-16102).

## 0.4.1 (2018-10-15)

- Add `documenteer.sphinxext.lssttasks` to the Sphinx extensions available for pipelines.lsst.io documentation builds.

- For pipelines.lsst.io builds, Documenteer ignores the `home/` directory that's created at the root of the `pipelines_lsst_io` directory.
  This directory is created as part of the ci.lsst.codes `sqre/infra/documenteer` job and shouldn't be part of the documentation build.

## 0.4.0 (2018-10-14)

- New directives and roles for documenting tasks in LSST Science Pipelines.

  - The `lsst-task-config-fields`, `lsst-task-config-subtasks`, and `lsst-config-fields` directives automatically generate documentation for configuration fields and subtasks in Tasks.
  - The `lsst-task-topic` and `lsst-config-topic` directives mark pages that document a given task or configuration class.
  - The `lsst-task`, `lsst-config`, and `lsst-config-field` roles create references to task topics or configuration fields.
  - The `lsst-task-api-summary` directive autogenerates a summary of the of a task's key APIs.
    This directive does not replace the autodoc-generated documentation for the task's class, but instead provides an affordance that creates a bridge from the task topic to the API reference topic.
  - The `lsst-tasks`, `lsst-cmdlinetasks`, `lsst-pipelinetasks`, `lsst-configurables`, and
    `lsst-configs` directives create listings of topics.
    These listings not only link to the topic, but also show a summary that's either extracted from the corresponding docstring or set through the `lsst-task-topic` or `lsst-config-topic` directives.
    These directives also generate a toctree.

- Added Astropy to the intersphinx configuration.

- Enabled `automodsumm_inherited_members` in the stackconf for stack documentation.
  This configuration is critical:

  1. It is actually responsible for ensuring that inherited members of classes appear in our docs.
  2. Without this, classes that have a `__slots__` attribute (typically through inheritance of a `collections.abc` class) won't have *any* of their members documented. See (DM-16102)(https://rubinobs.atlassian.net/browse/DM-16102) for discussion.

- `todo` directives are now hidden when using `build_pipelines_lsst_io_configs`.
  They are still shown, by default, for standalone package documentation builds, which are primarily developer-facing.

## 0.3.0 (2018-09-19)

- New `remote-code-block`, which works like the `literalinclude` directive, but allows you to include content from a URL over the web.
  You can use this directive after adding `documenteer.sphinxext` to the extensions list in a project's `conf.py`.

- New `module-toctree` and `package-toctree` directives.
  These create toctrees for modules and packages, respectively, in Stack documentation sites like pipelines.lsst.io.
  With these directives, we don't need to modify the `index.rst` file in https://github.com/lsst/pipelines_lsst_io each time new packages are added or removed.
  You can use this directive after adding `documenteer.sphinxext` to the extensions list in a project's `conf.py`.
  These directives include `skip` options for skipping certain packages and modules.

- New `stack-docs` command-line app.
  This replaces `build-stack-docs`, and now provides a subcommand interface: `stack-docs build` and `stack-docs clean`.
  This CLI is nice to use since it'll discover the root `conf.py` as long as you're in the root documentation repository.

- New `package-docs` command-line app.
  This CLI complements `stack-docs`, but is intended for single-package documentation.
  This effectively lets us replace the Sphinx Makefile (including the `clean` command).
  Using a packaged app lets us avoid SIP issues, as well as Makefile drift in individual packages.
  This CLI is nice to use since it'll discover the doc/ directory of a package as long as you're in the package's root directory, the doc/ directory, or a subdirectory of doc/.

- Refactored the Sphinx interface into `documenteer.sphinxrunner.run_sphinx`.
  This change lets multiple command-line front-ends to drive Sphinx.

- Various improvements to the configuration for LSST Stack-based documentation projects (`documenteer.sphinxconf.stackconf`):

  - Add `documenteer.sphinxconf.stackconf.build_pipelines_lsst_io_configs` to configure the Sphinx build of the https://github.com/lsst/pipelines_lsst_io repo.
    This pattern lets us share configurations between per-package documentation builds and the "stack" build in `pipelines_lsst_io`.

  - Replaced the third-party `astropy_helpers`_ package with the numpydoc_ and `sphinx-automodapi`_ packages.
    This helps reduce the number of extraneous dependencies needed for Stack documentation.

  - `autoclass_content` is now `"class"`, fitting the LSST DM standards for writing class docstrings, and not filling out `__init__` docstrings.

  - Added `scikit-learn` and `pandas` to the intersphinx configuration; removed h5py from intersphinx since it was never needed and conflicted with `daf_butler` documentation.

  - Removed the viewcode extension since that won't scale well with the LSST codebase.
    Ultimately we want to link to source on GitHub.

  - `_static/` directories are not needed and won't produce warnings if not present in a package.

  - Other internal cleanups for `documenteer.sphinxconf.stackconf`.

- Recognize a new field in the `metadata.yaml` files of Sphinx technotes called `exclude_patterns`.
  This is an array of file or directory paths that will be ignored by Sphinx during its build, as well as extensions like our `get_project_content_commit_date` for looking up commit date of content files.

- Updated to Sphinx >1.7.0, <1.8.0.
  Sphinx 1.8.0 is known to be incompatible with `documenteer.sphinxrunner`.

- Updated to lsst-sphinx-bootstrap-theme 0.3.x for pipelines docs.

- Switched to `setuptools_scm` for managing version strings.

- Improved the Travis CI-based PyPI release process.

## 0.2.7 (2018-03-09)

- Make `copyright` in `build_package_configs` an optional keyword argument. This is the way it should have always been to work with templated `conf.py` files.

## 0.2.6 (2018-02-20)

- Bump `astropy_helpers` version to >=3.0, <4.0 to get improved Sphinx extensions.
- Use setuptools `tests_require` to let us run tests without installing dependencies in the Python environment.
- Enable `python setup.py test` to run pytest.

## 0.2.5 (2017-12-20)

- Update to lsst-dd-rtd-theme 0.2.1

## 0.2.4 (2017-12-19)

- Add `edit_url` to the Jinja context for technotes.
  This enables "Edit on GitHub" functionality.
- Use lsst-dd-rtd-theme 0.2.0 for new branding, Edit on GitHub, and edition switching features for technotes.

## 0.2.3 (2017-07-28)

- Add support for additional DocuShare linking roles with `documenteer.sphinxext.lsstdocushare`.
  Supported handles now include: `ldm`, `lse`, `lpm`, `lts`, `lep`, `lca`, `lsstc`, `lcr`, `lcn`, `dmtr`, `spt`, `document`, `report`, `minutes`, `collection`, `sqr`, `dmtn`, `smtn`.
- Links made by the `documenteer.sphinxext.lsstdocushare` extension are now HTTPS.
- Pin the flake8 developer dependency to 3.3.0. Flake8 version 3.4 has changed how `noqa` comments are treated.

## 0.2.2 (2017-07-22)

- Add `documenteer.sphinxext.bibtex` extension to support LSST BibTeX entries that include a `docushare` field.
  Originally from [lsst-texmf](https://lsst-texmf.lsst.io).
  This extension is active in the technote Sphinx configuration.
- Add a `refresh-lsst-bib` command line program that downloads the latest LSST bib files from the [lsst-texmf GitHub repository](https://github.com/lsst/lsst-texmf).
  This program can be used by technote authors to update a technote's local bibliography set at any time.
- Added graceful defaults when a technote is being built without an underlying Git repository (catches exceptions from functions that seek Git metadata).
- Add a dependency upon the Requests library.

## 0.2.1 (2017-07-21)

- Rename configuration function for technotes: `documenteer.sphinxconfig.technoteconfig.configure_sphinx_design_doc` is now `documenteer.sphinxconfig.technoteconf.configure_technote`.
- Sphinx is no longer in the default intersphinx object list for technotes.
  This will speed up builds for documents that don't refer to Python APIs, and it still straightforward to configure on a per-project basis.
- The default revision timestamp for technotes is now derived from the most recent Git commit that modified a technote's content ('rst', and common image file formats).
  This is implemented with the new `documenteer.sphinxconfig.utils.get_project_content_commit_date()` function.
  This feature allows us to change technote infrastructure without automatically bumping the default revision date of the technote.

## 0.2.0 (2017-07-20)

- Add a new `build-stack-docs` command line executable.
  This executable links stack package documentation directories into a root documentation project and runs a Sphinx build.
  This is how we will build the https://pipelines.lsst.io documentation site.
  See [DMTN-030](https://dmtn-030.lsst.io/#documentation-as-code) for design details.
- **New system for installing project-specific dependencies.**
  We're using setuptools's `extras_require` feature to install different dependencies for technote and stack documentation projects.
  To install documenteer for a technote project, the new command is `pip install documenteer[technote]`.
  For stack documentation projects: `pip install documenteer[pipelines]`.
  Developers may use `pip install -e .[technote,pipelines,dev]`.
  This will allow us to install different Sphinx themes for different types of projects, for example.
- Pin Sphinx to >=1.5.0,<1.6.0 and docutils to 0.13.1. This is due to an API change in Sphinx's application `Config.init_values()`, which is used for making mock applications in Documenteer's unit tests.
- Move the `ddconfig.py` module for technical note Sphinx project configuration to the `documenteer.sphinxconfig.technoteconf` namespace for similarity with the `stackconf` module.
- Now using [versioneer](https://github.com/warner/python-versioneer) for version management.

## 0.1.11 (2017-03-01)

- Add `documenteer.sphinxconfig.utils.form_ltd_edition_name` to form LSST the Docs-like edition names for Git refs.
- Configure automated PyPI deployments with Travis.

## 0.1.10 (2016-12-14)

Includes prototype support for LSST Science Pipelines documentation, as part of `DM-6199 <https://rubinobs.atlassian.net/browse/DM-6199>`__:

- Added dependencies to [breathe](http://breathe.readthedocs.io/en/latest/), [astropy-helpers](https://github.com/astropy/astropy-helpers) and the [lsst-sphinx-bootstrap-theme](https://github.com/lsst-sqre/lsst-sphinx-bootstrap-theme) to generally coordinate LSST Science Pipelines documentation dependencies.
- Created `documenteer.sphinxconfig.stackconf` module to centrally coordinate Science Pipelines documentation configuration. Much of the configuration is based on [astropy-helper's Sphinx configuration](https://github.com/astropy/astropy-helpers/blob/master/astropy_helpers/sphinx/conf.py) since the LSST Science Pipelines documentation is heavily based upon Astropy's Sphinx theme and API reference generation infrastructure.
  Also includes prototype configuration for breathe (the doxygen XML bridge).
- Updated test harness (pytest and plugin versions).

## 0.1.9 (2016-07-08)

- Enhanced the `version` metadata change from v0.1.8 to work on Travis CI, by using the `TRAVIS_BRANCH`.

## 0.1.8 (2016-07-08)

- `last_revised` and `version` metadata in technote projects can now be set automatically from Git context if those fields are not explicitly set in `metadata.yaml`. DM-6916.
- Dependencies are now specified solely in `setup.py`, with `requirements.txt` being used for development dependencies only.
  This is consistent with advice from https://caremad.io/2013/07/setup-vs-requirement/.

## 0.1.7 (2016-06-02)

- Fix separator logic in JIRA tickets interpreted as lists.

## 0.1.6 (2016-06-01)

- Include `documenteer.sphinxext` in the default extensions for technote projects.

## 0.1.5 (2016-05-27)

- Fix rendering bug with `lpm`, `ldm`, and `lse` links.

## 0.1.4 (2016-05-27)

- Add roles for making mock references to code objects that don't have API references yet. E.g. `lclass`, `lfunc`. DM-6326.

## 0.1.3 (2016-05-24)

- Add roles for linking to `ls.st` links: `lpm`, `ldm`, and `lse`. DM-6181.
- Add roles for linking to JIRA tickets: `jira`, `jirab`, and `jirap`. DM-6181.

## 0.1.2 (2016-05-14)

- Include [sphinxcontrib-bibtex](https://sphinxcontrib-bibtex.readthedocs.io/) to Sphinx extensions available in technote projects. DM-6033.

## 0.1.0 (2015-11-23)

- Initial version
