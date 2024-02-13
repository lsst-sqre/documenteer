###############################################
Configuring Python projects in documenteer.toml
###############################################

If you are documenting a Python project that uses :file:`pyproject.toml` (or :file:`setup.cfg` and :file:`setup.py` in legacy situations) to define its project metadata, you can re-use that metadata in your Sphinx configuration rather than repeating it in :file:`documenteer.toml` by adding a ``project.python`` table

Walkthrough
===========

This is a minimal :file:`documenteer.toml` file for this project (Documenteer), where the Python package name is ``mypackage``:

.. code-block:: toml
   :caption: documenteer.toml

   [project]
   title = "My Package"
   copyright = "2015-2022 Association of Universities for Research in Astronomy, Inc. (AURA)"

   [project.python]
   package = "mypackage"

The key content from :file:`pyproject.toml` looks like this:

.. code-block:: toml
   :caption: ../pyproject.toml

   [project]
   name = "mypackage"
   # ...

   [project.urls]
   Homepage = "https://mypackage.lsst.io"
   Source = "https://github.com/lsst/mypackage"

Notice how the ``[project]`` table in :file:`documenteer.toml` is quite short because most information is found from the Python project metadata:

- ``version`` is inferred from the installed package's metadata.
  If you use `setuptools_scm <https://github.com/pypa/setuptools_scm>`__, the version automatically increments with every commit or tag.

- ``base_url`` is inferred from the ``Homepage`` field in ``[project.urls]`` in :file:`pyproject.toml`.

- ``github_url`` is inferred from the ``Source`` field in ``[project.urls]`` in :file:`pyproject.toml`.

.. important::

   The Python package must be installed in the environment where you run Sphinx to use this feature.
   For example, in your project's GitHub Actions workflow you must install the package with ``pip install .`` before running Sphinx.

   You cannot simply set the ``PYTHONPATH`` environment variable to add the package's source tree.
   Internally, Documenteer uses `importlib.metadata` to read the installed package's metadata.
   This is also why EUPS-installed packages are not supported by the ``[project.python]`` feature.

Overriding Python packaging metadata
====================================

You can always override the metadata from ``pyproject.toml`` by setting fields explicitly in the ``[project]`` table.
For example, to fix the version as "1.0.0":

.. code-block:: toml
   :caption: documenteer.toml

   [project]
   title = "My Package"
   copyright = "2015-2022 Association of Universities for Research in Astronomy, Inc. (AURA)"
   version = "1.0.0"

   [project.python]
   package = "mypackage"

Using alternative labels in pyproject.toml's [project.urls]
===========================================================

Documenteer defaults to ``Homepage`` and ``Source`` as the labels for the documentation and GitHub homepages, respectively, in ``[project.urls]`` table of :file:`pyproject.toml`.
You can change these defaults in :file:`documenteer.toml`:

.. code-block:: toml
   :caption: documenteer.toml

   [project]
   title = "My Package"
   copyright = "2015-2022 Association of Universities for Research in Astronomy, Inc. (AURA)"

   [project.python]
   package = "mypackage"
   documentation_url_key = "Docs"
   github_url_key = "Repository"

And the corresponding :file:`pyproject.toml` using those labels:

.. code-block:: toml
   :caption: ../pyproject.toml

   [project]
   name = "mypackage"
   # ...

   [project.urls]
   Docs = "https://mypackage.lsst.io"
   Repository = "https://github.com/lsst/mypackage"
