.. default-domain:: rst

.. _guide-citation-card:

##############
Citation cards
##############

A site that is published with a DOI is that DOI's *landing page*, and a landing page is expected to show the reader a complete bibliographic citation with the DOI written as a resolvable ``https://doi.org/`` link.
The ``citation-card`` directive is the surface that does this: it renders one of the site's citations as a card carrying the full citation, the citation's label, and its note.

Cards are the page-level counterpart to the citations in the site footer, and are the right tool for a dedicated "Citing this site" page, or for a section of the home page.

Declaring the citations
=======================

A card renders a citation the site has already declared in the :ref:`[[project.citations]] <guide-project-citations>` array of :file:`documenteer.toml`; the directive never carries bibliographic fields of its own.
A site that documents a data release typically declares two citations — the release itself, which this site is the landing page for, and the paper that describes it:

.. code-block:: toml

   # documenteer.toml

   [[project.citations]]
   doi = "10.71929/rubin/2570308"
   label = "Dataset"
   self = true
   note = "To be used when citing the DP2 dataset and this documentation."
   title = "Data Preview 2"
   publisher = "Vera C. Rubin Observatory"
   date = 2025-06-30
   authors = [{ name = "Vera C. Rubin Observatory" }]

   [[project.citations]]
   doi = "10.5281/zenodo.1234567"
   label = "Paper"
   title = "The Data Preview 2 release"
   publisher = "Zenodo"
   date = 2025-06-30
   authors = [{ name = "Vera C. Rubin Observatory" }]

Directive
=========

.. directive:: .. citation-card:: [label]

   Render one of the site's :ref:`[[project.citations]] <guide-project-citations>` entries as a card.

   The card shows the citation's :ref:`label <guide-project-citations-label>`, the full bibliographic citation with the DOI as a ``https://doi.org/`` hyperlink, and the citation's :ref:`note <guide-project-citations-note>`.
   An entry that sets no note renders no note, and an entry with no label renders no label.

   **Default: the site's own citation**

   With no argument, the card renders the entry marked :ref:`self = true <guide-project-citations-self>` — the work whose DOI landing page this site is:

   .. tab-set::

      .. tab-item:: reStructuredText
         :sync: rst

         .. code-block:: rst

            .. citation-card::

      .. tab-item:: markdown
         :sync: md

         .. code-block:: markdown

            :::{citation-card}
            :::

   With the configuration above, that card reads:

   .. code-block:: text

      DATASET

      Vera C. Rubin Observatory (2025). Data Preview 2. Vera C. Rubin
      Observatory. https://doi.org/10.71929/rubin/2570308

      To be used when citing the DP2 dataset and this documentation.

   **Selecting a citation by label**

   The optional argument is the :ref:`label <guide-project-citations-label>` of the entry to render, so a page can also show a citation that isn't the site's own:

   .. tab-set::

      .. tab-item:: reStructuredText
         :sync: rst

         .. code-block:: rst

            .. citation-card:: Paper

      .. tab-item:: markdown
         :sync: md

         .. code-block:: markdown

            :::{citation-card} Paper
            :::

   **Options**

   ``class``
       Additional CSS classes to set on the card.

   ``name``
       A cross-reference target for the card.

Unresolvable cards
==================

A card that names a label no entry carries — and a card with no argument on a site where no entry is marked ``self = true`` — renders nothing and emits a build warning naming the labels the site does declare.

That warning carries the subtype ``documenteer.citation_card``, so a site that knowingly keeps such a card can stop it from failing a warnings-as-errors (``-W``) build:

.. code-block:: python

   # conf.py
   suppress_warnings = ["documenteer.citation_card"]

Related metadata
================

Declaring ``[[project.citations]]`` also makes the site's DOI machine-readable: every page's ``<head>`` carries the ``self`` citation's DOI as Highwire and Dublin Core meta tags, along with a schema.org JSON-LD description of the site and the works it cites.
See :ref:`[[project.citations]] <guide-project-citations>` for the full field reference.
