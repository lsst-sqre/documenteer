###########################################
Redirecting pages when reorganizing content
###########################################

As a documentation site grows, its natural for content to need to move.
If pages are moved or renamed, you should create a redirect from the old page path to the new one so that users won't be orphaned by out-of-date links and bookmarks.
Documenteer supports this with the :ref:`guide-sphinx-redirects` table in the :file:`documenteer.toml` configuration file.

Adding a page redirect in documenteer.toml
==========================================

As an example, consider the page at :file:`old-page.rst` has moved to :file:`some-dir/new-page.rst`.
To create a redirect from the old page to the new one, add the following to the :file:`documenteer.toml` file:

.. code-block:: toml
   :caption: documenteer.toml

   [sphinx.redirects]
   "old-page.rst" = "some-dir/new-page.rst"

These paths are relative to the documentation project's root directory (where :file:`conf.py` and :file:`documenteer.toml` are located) and include the file extension (e.g., :file:`.rst` or :file:`.md`).

The table accepts an arbitrary number of redirects:

.. code-block:: toml
   :caption: documenteer.toml

   [sphinx.redirects]
   "old-page.rst" = "some-dir/new-page.rst"
   "foo.rst" = "bar.rst"

Redirects for deleted pages
===========================

Besides pages that have been moved, you can use this feature for pages that have been deleted.
Choose an existing path that is most relevant to the deleted page and redirect it to the new location.

.. code-block:: toml
   :caption: documenteer.toml

   [sphinx.redirects]
   "deleted-page.rst" = "index.rst"
