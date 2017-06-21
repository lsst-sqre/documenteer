Change Log
==========

Unreleased
----------

- Use `versioneer <https://github.com/warner/python-versioneer>`_ for version management.
- Move the ``ddconfig.py`` module for technical note Sphinx project configuration to the ``documenteer.sphinxconfig.technoteconf`` namespace for similarity with the ``stackconf`` module.

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
