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

extensions
----------

|optional|

A list of Sphinx extensions to append to the extensions included in the Documenteer configuration preset (see |documenteer.conf.guide|).
Duplicate extensions are ignored.

Remember that additional packages may need to be added to your project's Python dependencies (such as in a ``requirements.txt`` or ``pyproject.toml`` file).

nitpicky
--------

|optional|

Set to ``true`` to escalate Sphinx warnings to errors, which is useful for leveraging CI to notify you of any syntax errors.
The default is ``false``.

.. code-block:: toml

   [sphinx]
   nitpicky = true

See ``nitpick_ignore`` and ``nitpick_ignore_regex`` for ways to suppress unavoidable errors.

nitpick_ignore
--------------

|optional|

A list of Sphinx warnings to ignore.
Each item is a tuple of two items:

1. ``type``, often the reStructuredText role or directive creating the error/warning.
2. ``target``, often the argument to the reStructuredText role.

.. code-block:: toml

   [sphinx]
   nitpick_ignore = [
     ["py:class", "fastapi.applications.FastAPI"],
     ["py:class", "httpx.AsyncClient"],
     ["py:class", "pydantic.main.BaseModel"],
   ]

This configuration extends the Sphinx ``nitpick_ignore`` configuration.

nitpick_ignore_regex
--------------------

|optional|

A list of Sphinx warnings to ignore, formatted as regular expressions.
Each item is a tuple of two items:

1. ``type``, a regular expression of the warning type.
2. ``target``, a regular expression of the warning target.

.. code-block:: toml

   [sphinx]
   nitpick_ignore_regex = [
     ['py:.*', 'fastapi.*'],
     ['py:.*', 'httpx.*'],
     ['py:.*', 'pydantic*'],
   ]

.. tip::

   Use single quotes for literal strings in TOML.

This configuration extends the Sphinx ``nitpick_ignore_regex`` configuration.

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

[sphinx.intersphinx]
====================

|optional|

Configurations related to Intersphinx_ for linking to other Sphinx projects.

[sphinx.intersphinx.projects]
=============================

|optional|

A table of Sphinx projects.
The labels are targets for the :external+sphinx:rst:role:`external` role.
The values are URLs to the root of Sphinx documentation projects.

.. code-block:: toml

   [sphinx.intersphinx.projects]
   sphinx = "https://www.sphinx-doc.org/en/master/"
   documenteer = "https://documenteer.lsst.io"
   python = "https://docs.python.org/3/"

See the Intersphinx_ documentation for details on linking to other Sphinx projects.

[sphinx.linkcheck]
==================

|optional|

Configurations related to Sphinx's linkcheck_ builder.

ignore
------

|optional|

List of URL regular expressions patterns to ignore checking.
These are appended to the ``linkcheck_ignore`` configuration.
