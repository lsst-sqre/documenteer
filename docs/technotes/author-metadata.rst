###########################
Maintaining author metadata
###########################

The list of authors for a technote is maintained in the :file:`technote.toml` file.
This page describes how to add and update author listings.

The connection to authordb.yaml
===============================

The author metadata in a technote's :file:`technote.toml` file is *derived* from Rubin Observatory's author database, `authordb.yaml`_, located in the https://github.com/lsst/lsst-texmf repository.
The ``internal_id`` field in :file:`technote.toml` points to the author's entry in `authordb.yaml`_.
This is done so that team members are identified consistently across Rubin Observatory documents and publications.

For example, an author with an ID of ``sickj`` is represented in :file:`technote.toml` as:

.. code-block:: toml
   :caption: technote.toml
   :emphasize-lines: 3

   [[technote.authors]]
   name = {given = "Jonathan", family = "Sick"}
   internal_id = "sickj"
   orcid = "https://orcid.org/0000-0003-3001-676X"
   [[technote.authors.affiliations]]
   name = "Rubin Observatory Project Office"
   internal_id = "RubinObs"
   address = "950 N. Cherry Ave., Tucson, AZ 85719, USA"

The corresponding entry in `authordb.yaml`_ is:

.. code-block:: yaml
   :caption: authordb.yaml in lsst/lsst-texmf
   :emphasize-lines: 3

   authors:
     # [...]
     sickj:
       affil:
       - RubinObs
       altaffil: []
       initials: Jonathan
       name: Sick
       orcid: 0000-0003-3001-676X

The highlighted lines, above, show the author ID that connects these metadata sets.

A consequence of this connection is that all technote authors must have an entry in `authordb.yaml`_.
You can add and update entries by submitting a pull request to the https://github.com/lsst/lsst-texmf repository.

Adding a new author
===================

Given an author ID from `authordb.yaml`_, you can add that author to the technote's metadata by running the :command:`make add-author` command:

.. prompt:: bash

   make add-author

That command prompts you for the author ID, and then appends the author to the end of the author listing in :file:`technote.toml` (existing authors are updated in place).

Authors are represented in :file:`technote.toml` as as individual tables under the ``technote.authors`` *array of tables*.
A technote with Sick as the first author and Economou as the second author would look like:

.. code-block:: toml
   :caption: technote.toml

   [[technote.authors]]
   name = {given = "Jonathan", family = "Sick"}
   internal_id = "sickj"
   orcid = "https://orcid.org/0000-0003-3001-676X"
   [[technote.authors.affiliations]]
   name = "Rubin Observatory Project Office"
   internal_id = "RubinObs"
   address = "950 N. Cherry Ave., Tucson, AZ 85719, USA"

   [[technote.authors]]
   name = {given = "Frossie", family = "Economou"}
   internal_id = "economouf"
   orcid = "https://orcid.org/0000-0002-8333-7615"
   [[technote.authors.affiliations]]
   name = "Rubin Observatory Project Office"
   internal_id = "RubinObs"
   address = "950 N. Cherry Ave., Tucson, AZ 85719, USA"

To change the order of authors, you can move the ``[[technote.authors]]`` tables around in the file.
Don't forget to keep the ``[[technote.authors.affiliations]]`` tables with their corresponding authors.

Updating author metadata
========================

Occasionally the author metadata in `authordb.yaml`_ will change.
To update the author metadata in your technote, run:

.. prompt:: bash

   make sync-authors

Related documentation
=====================

- :external+technote:ref:`Schema for the [[technote.authors]] table in technote.toml in the Technote package documentation <toml-technote-authors>`
- `Configuring authors <https://technote.lsst.io/user-guide/configure-authors.html>`__, from the Technote package documentation
