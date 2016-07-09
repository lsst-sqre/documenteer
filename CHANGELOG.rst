Changelog for documenteer
=========================

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
