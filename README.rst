.. image:: https://img.shields.io/badge/documenteer-lsst.io-brightgreen.svg
   :target: https://documenteer.lsst.io
   :alt: Documentation
.. image:: https://img.shields.io/pypi/v/documenteer.svg?style=flat-square
   :target: https://pypi.python.org/pypi/documenteer
   :alt: PyPI
.. image:: https://img.shields.io/pypi/l/documenteer.svg?style=flat-square
   :alt: MIT license
   :target: https://pypi.python.org/pypi/documenteer
.. image:: https://img.shields.io/pypi/wheel/documenteer.svg?style=flat-square
   :alt: Uses wheel
   :target: https://pypi.python.org/pypi/documenteer
.. image:: https://img.shields.io/pypi/pyversions/documenteer.svg?style=flat-square
   :alt: For Python 3.7+
   :target: https://pypi.python.org/pypi/documenteer
.. image:: https://github.com/lsst-sqre/documenteer/workflows/CI/badge.svg
   :target: https://github.com/lsst-sqre/documenteer/actions?query=workflow%3ACI
   :alt: CI Service

###########
Documenteer
###########

Documenteer provides tools, extensions, and configurations for Rubin Observatory's Sphinx documentation projects, include technotes_ and stacks (such as the `LSST Science Pipelines`_).

.. _technotes: https://developer.lsst.io/project-docs/technotes.html
.. _LSST Science Pipelines: https://pipelines.lsst.io

For more information about Documenteer, see the documentation at https://documenteer.lsst.io.

Browse the `lsst-doc-engineering <https://github.com/topics/lsst-doc-engineering>`_ GitHub topic for more Rubin Observatory documentation engineering projects.

Quick installation:
===================

For technical note projects::

    pip install "documenteer[technote]"

For the stack projects (such as the `LSST Science Pipelines`_)::

   pip install "documenteer[pipelines]"

Features
========

Configurations
--------------

Documenteer includes preset configurations for common LSST DM Sphinx projects.
By using Documenteer, you can also ensure that Sphinx extensions required by these configurations are installed.

From the ``conf.py`` for technotes::

    from documenteer.conf.technote import *

From the ``conf.py`` for a stack package::

    from documenteer.conf.pipelinespkg import *

    project = "example"
    html_theme_options['logotext'] = project
    html_title = project
    html_short_title = project

From the ``conf.py`` for the LSST Science Pipelines documentation::

    from documenteer.conf.pipelines import *

Command-line tools
------------------

- `package-docs`_ builds documentation for individual packages in the LSST Science Pipelines
- `stack-docs`_ builds documentation for entire Stacks, such as the LSST Science Pipelines
- `refresh-lsst-bib`_ maintains LSST's common BibTeX files in individual technote repositories

.. _package-docs: https://documenteer.lsst.io/pipelines/package-docs-cli.html
.. _stack-docs: https://documenteer.lsst.io/pipelines/stack-docs-cli.html
.. _refresh-lsst-bib: https://developer.lsst.io/project-docs/technotes.html#using-bibliographies-in-restructuredtext-technotes

Sphinx extensions
-----------------

- Roles for linking to LSST documents and Jira tickets
- The ``remote-code-block`` directive
- The ``module-toctree`` and ``package-toctree`` directives for the LSST Science Pipelines documentation
- `Extensions for documenting LSST Science Pipelines tasks <https://documenteer.lsst.io/sphinxext/lssttasks.html>`__
- Support for LSST BibTeX files with sphinxcontrib-bibtex.
