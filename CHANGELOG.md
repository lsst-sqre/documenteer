# Change Log

## 0.8.0 (2023-07-23)

New features:

- Added a `-W` / `--warning-is-error` flag to the `package-docs build` and `stack-docs build` commands for Science Pipelines documentation builds. This flag causes Sphinx to treat warnings as errors, which is useful for CI builds.

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

- Link to technical notes, which are hosted on lsst.io, now linking directly to lsst.io rather than going through ls.st. This includes the sqr, dmtn, etc. roles and all the new roles mentioned above.
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
  Version 2.0.0 or later of `sphinxcontrib-bibtex`\_ is now required because of that package's API.

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
  [[DM-20866](https://jira.lsstcorp.org/browse/DM-20866)]

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

  [[DM-22698](https://jira.lsstcorp.org/browse/DM-22698), [DM-23094](https://jira.lsstcorp.org/browse/DM-23094), [DM-22461](https://jira.lsstcorp.org/browse/DM-22461)]

- Improved Sphinx runner (`documenteer.sphinxrunner`).
  [[DM-26768](https://jira.lsstcorp.org/browse/DM-26768)]

- Added static type checking using [mypy](https://mypy.readthedocs.io/en/stable/).
  [[DM-22717](https://jira.lsstcorp.org/browse/DM-22717), [DM-26288](https://jira.lsstcorp.org/browse/DM-26288)]

- Improved packaging, testing, and development environment:

  - PEP 518-ify the build process by adding a `pyproject.toml` file.
  - Removed the deprecated pytest-runner plugin.
  - Moved most of the packaging configuration to `setup.cfg`.
  - Adopted black and isort for code formatting.
  - Migrated to `tox` for running tests.
  - Migrated to `pre-commit` for running linters and code formatters.
  - Migrated to GitHub Actions from Travis CI.

  [`DM-22957 <https://jira.lsstcorp.org/browse/DM-22957>`_, `DM-26288 <https://jira.lsstcorp.org/browse/DM-26288>`_]

- Documentation improvements:

  - Added a new Developer guide and Release procedure guide.
  - Added an installation page.
  - Moved the Python API reference to its own page.
  - Improved the README to list features.

- Added GitHub community health features: contributing, support, and code of conduct files.

## 0.5.5 (2019-12-09)

- Technote configuration now uses `yaml.safe_load` instead of `yaml.load`.
  See the [pyyaml docs for details](<https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation>).
  [[DM-22537](https://jira.lsstcorp.org/browse/DM-22537)]

## 0.5.4 (2019-11-03)

- This new version of the technote sphinx theme should fix the edition link in the sidebar for non-main editions.
  [[DM-20839](https://jira.lsstcorp.org/browse/DM-20839)]

## 0.5.3 (2019-08-07)

- Enabled the `html_use_index` and `html_domain_indices` configurations for Stack documentation projects to enable automatic index generation.
  The `genindex` contains links to all command-line options and Python objects (Sphinx's domains).
  This also opens us up to a more general content index by way of the [index directive](https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#index-generating-markup).
  [[DM-20850](https://jira.lsstcorp.org/browse/DM-20850)]

- Fixed compatibility with docutils 0.15.
  Now Sphinx will control which version of docutils is used, which should now be 0.15.

- Also updated the intersphinx URL for Pandas to use https.

## 0.5.2 (2019-08-01)

- Add [sphinxcontrib.autoprogram](https://sphinxcontrib-autoprogram.readthedocs.io/en/stable/) to enable automated reference documentation of argparse-based command-line scripts.
  This extension is available with the `documenteer[pipelines]` installation extra and enabled by default for LSST Science Pipelines projects.
  [[DM-20767](https://jira.lsstcorp.org/browse/)]

- Update the official list of tested and supported Python versions to Python 3.6 and 3.7.

## 0.5.1 (2019-07-22)

- Pin docutils temporarily to `0.14`.
  The latest release, 0.15, is currently incompatible with the `:jira:` role.

## 0.5.0 (2019-02-11)

- The stack documentation build now requires that packages be explicitly required by the main documentation project's EUPS table file.
  Before, a package only needed a `doc/manifest.yaml` file and to be currently set up in the EUPS environment to be linked into the documentation build.
  This would lead to packages being included in a documentation build despite not being a part of that stack product.
  [[DM-17765](https://jira.lsstcorp.org/browse/DM-17765)]

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
  [[DM-17065](https://jira.lsstcorp.org/browse/DM-17065)]

- This release also added some new substitutions to the `rst_epilog` of stack-based projects:

  - `|eups-tag|` --- the current EUPS tag, based on the `EUPS_TAG` environment variable.
  - `|eups-tag-mono|` --- monospace typeface version of `|eups-tag|`.
  - `|eups-tag-bold|` --- bold typeface version of `|eups-tag|`.

  The `|current-release|` substitution is no longer available.

- Fixed some bugs with the display of copyrights in stack-based projects.

- The project's name is also used as the `logotext` at the top of the page for stack-based projects.
  Previously the `logotext` would always be "LSST Science Pipelines."
  [[DM-17263](https://jira.lsstcorp.org/browse/DM-17263)]

- Added the following projects to the intersphinx inventory of stack-based projects:

  - `firefly_client`
  - `astro_metadata_translator`

## 0.4.5 (2019-02-06)

- Added a new `lso` role for linking to LSST Operations documents in DocuShare.

## 0.4.4 (2019-02-05)

- Updated scikit-learn's intersphinx inventory URL (now available as HTTPS) in the `documenteer.sphinxconfig.stackconf`.
- Fixed the `lsst-task-config-subtasks` directive so that it can introspect items in an `lsst.pex.config` `Registry` that are wrapped by a `ConfigurableWrapper`. [(DM-17661)[https://jira.lsstcorp.org/browse/DM-17661]]

## 0.4.3 (2018-11-30)

- Pin [sphinxcontrib-bibtex](https://github.com/mcmtroffaes/sphinxcontrib-bibtex) to version 0.4.0 since later versions are incompatible with Sphinx <1.8.0.
  [[DM-16651](https://jira.lsstcorp.org/browse/DM-16651)]

## 0.4.2 (2018-11-01)

- Handle cases where an object does not have a docstring in `documenteer.sphinxext.lssttasks.taskutils.get_docstring`.
  This improves the reliability of the `lsst-task-api-summary` directive.
  See (DM-16102)(https://jira.lsstcorp.org/browse/DM-16102).

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
  2. Without this, classes that have a `__slots__` attribute (typically through inheritance of a `collections.abc` class) won't have _any_ of their members documented. See (DM-16102)(https://jira.lsstcorp.org/browse/DM-16102) for discussion.

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

  - Replaced the third-party `astropy_helpers`_ package with the numpydoc_ and `sphinx-automodapi`\_ packages.
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

Includes prototype support for LSST Science Pipelines documentation, as part of `DM-6199 <https://jira.lsstcorp.org/browse/DM-6199>`\_\_:

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

- Add roles for linking to ls.st links: `lpm`, `ldm`, and `lse`. DM-6181.
- Add roles for linking to JIRA tickets: `jira`, `jirab`, and `jirap`. DM-6181.

## 0.1.2 (2016-05-14)

- Include [sphinxcontrib-bibtex](https://sphinxcontrib-bibtex.readthedocs.io/) to Sphinx extensions available in technote projects. DM-6033.

## 0.1.0 (2015-11-23)

- Initial version
