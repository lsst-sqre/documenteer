Change Log
==========

0.4.1 (2018-10-15)
------------------

- Add ``documenteer.sphinxext.lssttasks`` to the Sphinx extensions available for pipelines.lsst.io documentation builds.

- For pipelines.lsst.io builds, Documenteer ignores the ``home/`` directory that's created at the root of the ``pipelines_lsst_io`` directory.
  This directory is created as part of the ci.lsst.codes ``sqre/infra/documenteer`` job and shouldn't be part of the documentation build.

0.4.0 (2018-10-14)
------------------

- New directives and roles for documenting tasks in LSST Science Pipelines.

  - The ``lsst-task-config-fields``, ``lsst-task-config-subtasks``, and ``lsst-config-fields`` directives automatically generate documentation for configuration fields and subtasks in Tasks.
  - The ``lsst-task-topic`` and ``lsst-config-topic`` directives mark pages that document a given task or configuration class.
  - The ``lsst-task``, ``lsst-config``, and ``lsst-config-field`` roles create references to task topics or configuration fields.
  - The ``lsst-task-api-summary`` directive autogenerates a summary of the of a task's key APIs.
    This directive does not replace the autodoc-generated documentation for the task's class, but instead provides an affordance that creates a bridge from the task topic to the API reference topic.
  - The ``lsst-tasks``, ``lsst-cmdlinetasks``, ``lsst-pipelinetasks``, ``lsst-configurables``, and
    ``lsst-configs`` directives create listings of topics.
    These listings not only link to the topic, but also show a summary that's either extracted from the corresponding docstring or set through the ``lsst-task-topic`` or ``lsst-config-topic`` directives.
    These directives also generate a toctree.

- Added Astropy to the intersphinx configuration.

- Enabled ``automodsumm_inherited_members`` in the stackconf for stack documentation.
  This configuration is critical:

  1. It is actually responsible for ensuring that inherited members of classes appear in our docs.
  2. Without this, classes that have a ``__slots__`` attribute (typically through inheritance of a ``collections.abc`` class) won't have *any* of their members documented. See https://jira.lsstcorp.org/browse/DM-16102 for discussion.

- ``todo`` directives are now hidden when using ``build_pipelines_lsst_io_configs``.
  They are still shown, by default, for standalone package documentation builds, which are primarily developer-facing.

0.3.0 (2018-09-19)
------------------

- New ``remote-code-block``, which works like the ``literalinclude`` directive, but allows you to include content from a URL over the web.
  You can use this directive after adding ``documenteer.sphinxext`` to the extensions list in a project's ``conf.py``.

- New ``module-toctree`` and ``package-toctree`` directives.
  These create toctrees for modules and packages, respectively, in Stack documentation sites like pipelines.lsst.io.
  With these directives, we don't need to modify the ``index.rst`` file in https://github.com/lsst/pipelines_lsst_io each time new packages are added or removed.
  You can use this directive after adding ``documenteer.sphinxext`` to the extensions list in a project's ``conf.py``.
  These directives include ``skip`` options for skipping certain packages and modules.

- New ``stack-docs`` command-line app.
  This replaces ``build-stack-docs``, and now provides a subcommand interface: ``stack-docs build`` and ``stack-docs clean``.
  This CLI is nice to use since it'll discover the root conf.py as long as you're in the root documentation repository.

- New ``package-docs`` command-line app.
  This CLI complements ``stack-docs``, but is intended for single-package documentation.
  This effectively lets us replace the Sphinx Makefile (including the ``clean`` command).
  Using a packaged app lets us avoid SIP issues, as well as Makefile drift in individual packages.
  This CLI is nice to use since it'll discover the doc/ directory of a package as long as you're in the package's root directory, the doc/ directory, or a subdirectory of doc/.

- Refactored the Sphinx interface into ``documenteer.sphinxrunner.run_sphinx``.
  This change lets multiple command-line front-ends to drive Sphinx.

- Various improvements to the configuration for LSST Stack-based documentation projects (``documenteer.sphinxconf.stackconf``):

  - Add ``documenteer.sphinxconf.stackconf.build_pipelines_lsst_io_configs`` to configure the Sphinx build of the https://github.com/lsst/pipelines_lsst_io repo.
    This pattern lets us share configurations between per-package documentation builds and the "stack" build in ``pipelines_lsst_io``.

  - Replaced the third-party `astropy_helpers`_ package with the numpydoc_ and `sphinx-automodapi`_ packages.
    This helps reduce the number of extraneous dependencies needed for Stack documentation.

  - ``autoclass_content`` is now ``"class"``, fitting the LSST DM standards for writing class docstrings, and not filling out ``__init__`` docstrings.

  - Added ``scikit-learn`` and ``pandas`` to the intersphinx configuration; removed h5py from intersphinx since it was never needed and conflicted with ``daf_butler`` documentation.

  - Removed the viewcode extension since that won't scale well with the LSST codebase.
    Ultimately we want to link to source on GitHub.

  - ``_static/`` directories are not needed and won't produce warnings if not present in a package.

  - Other internal cleanups for ``documenteer.sphinxconf.stackconf``.

- Recognize a new field in the ``metadata.yaml`` files of Sphinx technotes called ``exclude_patterns``.
  This is an array of file or directory paths that will be ignored by Sphinx during its build, as well as extensions like our ``get_project_content_commit_date`` for looking up commit date of content files.

- Updated to Sphinx >1.7.0, <1.8.0.
  Sphinx 1.8.0 is known to be incompatible with ``documenteer.sphinxrunner``.

- Updated to lsst-sphinx-bootstrap-theme 0.3.x for pipelines docs.

- Switched to ``setuptools_scm`` for managing version strings.

- Improved the Travis CI-based PyPI release process.

0.2.7 (2018-03-09)
------------------

- Make ``copyright`` in ``build_package_configs`` an optional keyword argument. This is the way it should have always been to work with templated ``conf.py`` files.

0.2.6 (2018-02-20)
------------------

- Bump ``astropy_helpers`` version to >=3.0, <4.0 to get improved Sphinx extensions.
- Use setuptools ``tests_require`` to let us run tests without installing dependencies in the Python environment.
- Enable ``python setup.py test`` to run pytest.

0.2.5 (2017-12-20)
------------------

- Update to lsst-dd-rtd-theme 0.2.1

0.2.4 (2017-12-19)
------------------

- Add ``edit_url`` to the Jinja context for technotes.
  This enables "Edit on GitHub" functionality.
- Use lsst-dd-rtd-theme 0.2.0 for new branding, Edit on GitHub, and edition switching features for technotes.

0.2.3 (2017-07-28)
------------------

- Add support for additional DocuShare linking roles with ``documenteer.sphinxext.lsstdocushare``.
  Supported handles now include: ``ldm``, ``lse``, ``lpm``, ``lts``, ``lep``, ``lca``, ``lsstc``, ``lcr``, ``lcn``, ``dmtr``, ``spt``, ``document``, ``report``, ``minutes``, ``collection``, ``sqr``, ``dmtn``, ``smtn``.
- Links made by the ``documenteer.sphinxext.lsstdocushare`` extension are now HTTPS.
- Pin the flake8 developer dependency to 3.3.0. Flake8 version 3.4 has changed how ``noqa`` comments are treated.

0.2.2 (2017-07-22)
------------------

- Add ``documenteer.sphinxext.bibtex`` extension to support LSST BibTeX entries that include a ``docushare`` field.
  Originally from `lsst-texmf`_.
  This extension is active in the technote Sphinx configuration.
- Add a ``refresh-lsst-bib`` command line program that downloads the latest LSST bib files from the `lsst-texmf`_ GitHub repository.
  This program can be used by technote authors to update a technote's local bibliography set at any time.
- Added graceful defaults when a technote is being built without an underlying Git repository (catches exceptions from functions that seek Git metadata).
- Add a dependency upon the Requests library.

0.2.1 (2017-07-21)
------------------

- Rename configuration function for technotes: ``documenteer.sphinxconfig.technoteconfig.configure_sphinx_design_doc`` is now ``documenteer.sphinxconfig.technoteconf.configure_technote``.
- Sphinx is no longer in the default intersphinx object list for technotes.
  This will speed up builds for documents that don't refer to Python APIs, and it still straightforward to configure on a per-project basis.
- The default revision timestamp for technotes is now derived from the most recent Git commit that modified a technote's content ('rst', and common image file formats).
  This is implemented with the new ``documenteer.sphinxconfig.utils.get_project_content_commit_date()`` function.
  This feature allows us to change technote infrastructure without automatically bumping the default revision date of the technote.

0.2.0 (2017-07-20)
------------------

- Add a new ``build-stack-docs`` command line executable.
  This executable links stack package documentation directories into a root documentation project and runs a Sphinx build.
  This is how we will build the https://pipelines.lsst.io documentation site.
  See `DMTN-030 <https://dmtn-030.lsst.io/#documentation-as-code>`_ for design details.
- **New system for installing project-specific dependencies.**
  We're using setuptools's ``extras_require`` feature to install different dependencies for technote and stack documentation projects.
  To install documenteer for a technote project, the new command is ``pip install documenteer[technote]``.
  For stack documentation projects: ``pip install documenteer[pipelines]``.
  Developers may use ``pip install -e .[technote,pipelines,dev]``.
  This will allow us to install different Sphinx themes for different types of projects, for example.
- Pin Sphinx to >=1.5.0,<1.6.0 and docutils to 0.13.1. This is due to an API change in Sphinx's application ``Config.init_values()``, which is used for making mock applications in Documenteer's unit tests.
- Move the ``ddconfig.py`` module for technical note Sphinx project configuration to the ``documenteer.sphinxconfig.technoteconf`` namespace for similarity with the ``stackconf`` module.
- Now using `versioneer <https://github.com/warner/python-versioneer>`_ for version management.

0.1.11 (2017-03-01)
-------------------

- Add ``documenteer.sphinxconfi.utils.form_ltd_edition_name`` to form LSST the Docs-like edition names for Git refs.
- Configure automated PyPI deployments with Travis.

0.1.10 (2016-12-14)
-------------------

Includes prototype support for LSST Science Pipelines documentation, as part of `DM-6199 <https://jira.lsstcorp.org/browse/DM-6199>`__:

- Added dependencies to `breathe <http://breathe.readthedocs.io/en/latest/>`__, `astropy-helpers <https://github.com/astropy/astropy-helpers>`__ and the `lsst-sphinx-bootstrap-theme <https://github.com/lsst-sqre/lsst-sphinx-bootstrap-theme>`__ to generally coordinate LSST Science Pipelines documentation dependencies.
- Created ``documenteer.sphinxconfig.stackconf`` module to centrally coordinate Science Pipelines documentation configuration. Much of the configuration is based on `astropy-helper's Sphinx configuration <https://github.com/astropy/astropy-helpers/blob/master/astropy_helpers/sphinx/conf.py>`__ since the LSST Science Pipelines documentation is heavily based upon Astropy's Sphinx theme and API reference generation infrastructure.
  Also includes prototype configuration for breathe (the doxygen XML bridge).
- Updated test harness (pytest and plugin versions).

0.1.9 (2016-07-08)
------------------

- Enhanced the ``version`` metadata change from v0.1.8 to work on Travis CI, by using the ``TRAVIS_BRANCH``.

0.1.8 (2016-07-08)
------------------

- ``last_revised`` and ``version`` metadata in technote projects can now be set automatically from Git context if those fields are not explicitly set in ``metadata.yaml``. DM-6916.
- Dependencies are now specified solely in ``setup.py``, with ``requirements.txt`` being used for development dependencies only.
  This is consistent with advice from https://caremad.io/2013/07/setup-vs-requirement/.

0.1.7 (2016-06-02)
------------------

- Fix separator logic in JIRA tickets interpreted as lists.

0.1.6 (2016-06-01)
------------------

- Include ``documenteer.sphinxext`` in the default extensions for technote projects.

0.1.5 (2016-05-27)
------------------

- Fix rendering bug with ``lpm``, ``ldm``, and ``lse`` links.

0.1.4 (2016-05-27)
------------------

- Add roles for making mock references to code objects that don't have API references yet. E.g. ``lclass``, ``lfunc``. DM-6326.

0.1.3 (2016-05-24)
------------------

- Add roles for linking to ls.st links: ``lpm``, ``ldm``, and ``lse``. DM-6181.
- Add roles for linking to JIRA tickets: ``jira``, ``jirab``, and ``jirap``. DM-6181.

0.1.2 (2016-05-14)
------------------

- Include `sphinxcontrib.bibtex <https://github.com/mcmtroffaes/sphinxcontrib-bibtex>`_ to Sphinx extensions available in technote projects. DM-6033.

0.1.0 (2015-11-23)
------------------

- Initial version

.. _lsst-texmf: https://github.com/lsst/lsst-texmf
.. _astropy_helpers: https://pypi.org/project/astropy-helpers/
.. _`sphinx-automodapi`: https://pypi.org/project/sphinx-automodapi/
.. _numpydoc: https://pypi.org/project/numpydoc/
