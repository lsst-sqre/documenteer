.. _guide-improve-this-page:

##############################
The "Help improve" page footer
##############################

Every page in a user guide ends with a "Help improve this page" box, just below the previous/next page links.
The box gathers the page's improvement and provenance information in one place:

- An **"Edit this page on GitHub"** link that opens the page's source file in GitHub's editor, resolved by the :ref:`documenteer.ext.githubeditlink <documenteer-ext-githubeditlink>` extension.
- A **"This page was last modified on…"** timestamp derived from the page's Git commit history by the :ref:`documenteer.ext.lastmodified <documenteer-ext-lastmodified>` extension, localized to the reader's timezone.

Site-wide configuration
=======================

Each item is controlled by a setting in :file:`documenteer.toml`:

- :ref:`sphinx.show_github_edit_link <guide-project-show-github-edit-link>` toggles the edit link (default ``true``).
- :ref:`sphinx.show_last_updated <guide-project-show-last-updated>` toggles the timestamp (default ``true``).

When both are disabled — or neither applies to a page, as on generated pages like the search page — the box is omitted entirely.

Hiding the box on individual pages
==================================

Some pages don't benefit from the box; a site's home page, for example, often has a curated layout where the box would be a distraction.
Set the ``hide_content_footer`` file-wide metadata field to suppress the box on a single page.

In a reStructuredText file, add a field list at the very top of the file, before the title:

.. code-block:: rst
   :caption: index.rst

   :hide_content_footer:

   My homepage
   ===========

In a Markdown (MyST) file, use YAML front matter:

.. code-block:: markdown
   :caption: index.md

   ---
   hide_content_footer: true
   ---

   # My homepage

The rest of the site is unaffected; only pages carrying the field hide the box.

Printed pages and PDF output
============================

The box is interactive chrome, so it is omitted from printed output along with the rest of the page navigation — a link to GitHub's editor isn't actionable on paper.
In its place, printed pages end with a print-only provenance footer carrying the metadata that still matters in a fixed document: the "last modified" timestamp and the page's canonical URL.

The ``hide_content_footer`` metadata field suppresses the print footer along with the box.
