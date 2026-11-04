.. default-domain:: rst

.. _guide-citation-doi-role:

################
Inline DOI links
################

A card is a block, so a page that only needs to *mention* a work — the first bullet of an access list, a cell in a table of data products, a sentence pointing at the paper — cannot use one.
The ``doi`` role links a declared citation's DOI inline instead, reading the same :ref:`[[project.citations]] <guide-project-citations>` entries the card and the footer do.
A page that would otherwise write ``https://doi.org/10.26624/XWGH8202`` into a sentence by hand, or into a substitution that holds it, names the entry and gets whatever the configuration declares.
The links on this page are rendered from :ref:`this site's own citations <guide-citations>`.

.. role:: doi

   Link one of the site's :ref:`[[project.citations]] <guide-project-citations>` entries by its DOI.

   The role's content names the entry, resolved the same way the :ref:`citation-card <guide-citation-card>` directive's argument is: by :ref:`label <guide-project-citations-label>`, by :ref:`bibtex_key <guide-project-citations-bibtex-key>`, or by DOI in any spelling, matched exactly and case-sensitively.
   The link's text is the resolvable ``https://doi.org/`` URL, the form the Crossref and DataCite display guidelines ask for:

   .. tab-set::

      .. tab-item:: reStructuredText
         :sync: rst

         .. code-block:: rst

            The paper is published as :doi:`Paper`.

      .. tab-item:: markdown
         :sync: md

         .. code-block:: markdown

            The paper is published as {doi}`Paper`.

   That sentence renders as: The paper is published as :doi:`Paper`.

   Selecting by BibTeX key renders the same link: :doi:`2025ASPC..541..151S` is written ``:doi:`2025ASPC..541..151S```.

   **Custom link text**

   The standard ``text <target>`` spelling puts your own words on the link, for a sentence that should read as prose rather than as an identifier:

   .. tab-set::

      .. tab-item:: reStructuredText
         :sync: rst

         .. code-block:: rst

            For the background see :doi:`the ADASS paper <Paper>`.

      .. tab-item:: markdown
         :sync: md

         .. code-block:: markdown

            For the background see {doi}`the ADASS paper <Paper>`.

   That sentence renders as: For the background see :doi:`the ADASS paper <Paper>`.

   It is also what lets a sentence display one word over an entry it selects unambiguously, which is how a site whose products all need the word "TAP" writes them:

   .. code-block:: rst

      * TAP: :doi:`TAP <10.71929/rubin/3382540>`

   **Where it works**

   The role renders one external hyperlink and nothing else, so it composes wherever inline markup does: a sentence, a list item, a table cell, and the body of a ``replace`` substitution definition.
   A data product's "Access" list is the case it was added for:

   .. code-block:: rst

      Access
      ------

      * DOI: :doi:`Object catalog`
      * TAP table name: ``dp02_dc2_catalogs.Object``

   .. code-block:: rst

      .. |dp2_paper| replace:: :doi:`the DP2 paper <Paper>`

   There is no default entry: the role always names one.
   A role appears mid-sentence, where an implicit subject would be a guess at which of the site's works the sentence is about.

The role is a link, and only a link — no note, no BibTeX entry, no author-year text.
A page that *is* a work's landing page should therefore carry a :ref:`card <guide-citation-card>` for it and use the role only for short references elsewhere, since the card is what shows a reader the full citation and the entry they came for.

An entry located by a :ref:`url <guide-project-citations-url>` rather than a DOI, such as this site's own Software entry, cannot be linked with the role, because the link's text would not be a DOI; the build warns (see :ref:`guide-unresolvable-citations`).
Link such a work with ordinary hyperlink syntax, or show it with a card.

Citing works that are *not* among the site's own declared citations — a bibliography of the literature a guide discusses — is not what this role is for, and is not yet supported.
