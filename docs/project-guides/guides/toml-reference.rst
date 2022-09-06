##########################
documenteer.toml reference
##########################

Rubin's Sphinx user guide configuration with |documenteer.conf.guide| uses a :file:`documenteer.toml` file, located next to the Sphinx :file:`conf.py` file to configure metadata about the project.
This page describes the schema for this :file:`documenteer.toml` file.
For a step-by-step guide, see :doc:`configuration`.

[project] table
===============

The ``[project]`` table is where most of the project's metadata is set.

|required|

title
-----

|required|

Name of the project, used as titles throughout the documentation site.
The title can be different from the package name, if that's the local standard.

.. code-block:: toml

   [project]
   title = "Documenteer"

.. _guide-project-base-url:

base\_url
---------

|optional| |py-auto|

The root URL of the documentation project, used to set the `canonical URL link rel <https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/rel#attr-canonical>`__, which is valuable for search engines.

.. code-block:: toml

   [project]
   base_url = "https://documenteer.lsst.io"

copyright
---------

|optional|

The copyright statement, which should exclude the "Copyright" prefix.

.. code-block:: toml

   [project]
   copyright = "2015-2022 Association of Universities for Research in Astronomy, Inc. (AURA)"

.. _guide-project-github-url:

github\_url
-----------

|optional| |py-auto|

The URL for the project's GitHub source repository.
When set, a link to the repository is included in the site's header.

.. code-block:: toml

   [project]
   github_url = "https://github.com/lsst-sqre/documenteer"

.. _guide-project-version:

version
-------

|optional| |py-auto|

The project's version, which is set to the standard Sphinx ``version`` and ``release`` configuration variables.

[project.python]
================

|optional|

Projects that use a :file:`pyproject.toml` to set their build metadata can include a ``[project.python]`` table in :file:`documenteer.toml`.
With this, many metadata values are automatically detected — look for |py-auto| badges above.

.. note::

   If a value is directly set, such as :ref:`guide-project-version`, that value will override will override information discovered from the Python project itself.

.. seealso::

   :doc:`pyproject-configuration`

package
-------

|required|

This is the Python project's name, as set in the ``name`` field of the ``[project]`` table in :file:`pyproject.toml`.
*Note that the package name can be different from the Python module name.*
Setting this field actives automatic metadata discovery for Python projects.

.. code-block:: toml

   [project]

   [project.python]
   package = "documenteer"

documentation\_url\_key
-----------------------

|optional|

By default the :ref:`guide-project-base-url` is detected from the ``Homepage`` field in the ``[project.urls]`` table of :file:`pyproject.toml`.
If your documentation's URL is associated with a different field label, set that with ``documentation_url_key``.

github\_url\_key
----------------

|optional|

By default the :ref:`guide-project-github-url` is detected from the ``Source`` field in the ``[project.urls]`` table of :file:`pyproject.toml`.
If your GitHub repository's URL is associated with a different field label, set that with ``github_url_key``.

[sphinx]
========

|optional|

This ``[sphinx]`` table allows you to set a number of Sphinx configurations that you would normally set through the :file:`conf.py` file.

rst_epilog_file
---------------

|optional|

Set this as a path to a reStructuredText file (relative to :file:`documenteer.toml` and :file:`conf.py`) containing substitutions and link targets that are available to all documentation pages.
This configuration sets Sphinx's ``rst_epilog`` configuration.
If set, the file is also included in the Sphinx source ignore list to prevent it from becoming a standalone page.

.. code-block:: toml
   :caption: documenteer.toml

    [sphinx]
    rst_epilog_file = "_rst_epilog.rst"

.. code-block:: rst
   :caption: _rst_epilog.rst

   .. _Astropy Project: https://www.astropy.org

   .. |required| replace:: :bdg-primary-line:`Required`
   .. |optional| replace:: :bdg-secondary-line:`Optional`
