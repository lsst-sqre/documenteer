#############################################################
Describing the document status (draft, deprecated, or stable)
#############################################################

Technotes are continuously updated on the web as you add commits and merge pull requests.
Your "drafts" are visible to the rest of the observatory, and even the public, to speed up collaboration and provide transparency.
You can communicate the status of the document by setting metadata in :file:`technote.toml`.
For example, you can specify that the technote is an incomplete draft, or that the technote is deprecated and is now replaced by another set of documents.

Setting "draft" status
======================

If the technote is incomplete and being actively written, you can set the status to "draft:"

.. code-block:: toml
   :caption: technote.toml

   [technote.state]
   status = "draft"

Setting "stable" status
=======================

If the technote is complete, accurate and no longer being actively worked upon, you can set the status to "stable:"

.. code-block:: toml
   :caption: technote.toml

   [technote.state]
   status = "stable"

This is the default state if one is not specified in :file:`technote.toml`.

Setting "deprecated" status
===========================

If your technote is no longer accurate or relevant, you can mark it as deprecated:

.. code-block:: toml
   :caption: technote.toml

   [technote.state]
   status = "deprecated"
   note = "This technote is deprecated because [...]"

If the technote has been replaced by one or more other documents, you can link to them with a ``supersceding_urls`` array:

.. code-block:: toml
   :caption: technote.toml

   [technote.state]
   status = "deprecated"
   note = "This technote is deprecated because [...]"

   [[technote.state.supersceding_urls]]
   title = "New technote"
   url = "https://example.lsst.io/"

   [[technote.state.supersceding_urls]]
   title = "Another document"
   url = "https://example-two.lsst.io/"
