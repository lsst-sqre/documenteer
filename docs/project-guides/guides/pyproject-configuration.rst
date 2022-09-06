###############################################
Configuring Python projects in documenteer.toml
###############################################

If you are documenting a Python project that uses :file:`pyproject.toml` (or :file:`setup.cfg` and :file:`setup.py` in legacy situations) to define its project metadata, you can re-use that metadata in your Sphinx configuration rather than repeating it in :file:`documenteer.toml` by adding a ``project.python`` table

Walkthrough
===========

This is a minimal :file:`documenteer.toml` file for this project (Documenteer), where the Python package name is ``documenteer``:

.. code-block:: toml
   :caption: documenteer.toml

   [project]
   title = "Documenteer"
   copyright = "2015-2022 Association of Universities for Research in Astronomy, Inc. (AURA)"

   [project.python]
   package = "documenteer"

The key content from :file:`pyproject.toml` looks like this:

.. code-block:: toml
   :caption: ../pyproject.toml

   [project]
   name = "documenteer"
   # ...

   [project.urls]
   Homepage = "https://documenteer.lsst.io"
   Source = "https://github.com/lsst-sqre/documenteer"

Notice how the ``[project]`` table in :file:`documenteer.toml` is quite short because most information is found from the Python project metadata:

- ``version`` is inferred from the installed package's metadata.
  If you use `setuptools_scm <https://github.com/pypa/setuptools_scm>`__, the version automatically increments with every commit or tag.

- ``base_url`` is inferred from the ``Homepage`` field in ``[project.urls]`` in :file:`pyproject.toml`.

- ``github_url`` is inferred from the ``Source`` field in ``[project.urls]`` in :file:`pyproject.toml`.

Overriding Python packaging metadata
====================================

You can always override the metadata from ``pyproject.toml`` by setting fields explicitly in the ``[project]`` table.
For example, to fix the version as "1.0.0":

.. code-block:: toml
   :caption: documenteer.toml

   [project]
   title = "Documenteer"
   copyright = "2015-2022 Association of Universities for Research in Astronomy, Inc. (AURA)"
   version = "1.0.0"

   [project.python]
   package = "documenteer"

Using alternative labels in pyproject.toml's [project.urls]
===========================================================

Documenteer defaults to ``Homepage`` and ``Source`` as the labels for the documentation and GitHub homepages, respectively, in ``[project.urls]`` table of :file:`pyproject.toml`.
You can change these defaults in :file:`documenteer.toml`:

.. code-block:: toml
   :caption: documenteer.toml

   [project]
   title = "Documenteer"
   copyright = "2015-2022 Association of Universities for Research in Astronomy, Inc. (AURA)"

   [project.python]
   package = "documenteer"
   documentation_url_key = "Docs"
   github_url_key = "Repository"

And the corresponding :file:`pyproject.toml` using those labels:

.. code-block:: toml
   :caption: ../pyproject.toml

   [project]
   name = "documenteer"
   # ...

   [project.urls]
   Docs = "https://documenteer.lsst.io"
   Repository = "https://github.com/lsst-sqre/documenteer"
