#############################
Citing references with BibTeX
#############################

Technotes include built-in support for citing references with BibTeX. Any bibitem from `lsst-texmf's bibliography files <https://github.com/lsst/lsst-texmf/tree/main/texmf/bibtex/bib>`__ is available for citation.
You can also define your own BibTeX entries in a local bib files.

Set up references section
=========================

To use BibTeX references in your technote, add a "References" section at the end of the main content with a ``bibliography`` directive:

.. tab-set::
   :sync-group: markup

   .. tab-item:: RST
      :sync: rst

      .. code-block:: rst

         References
         ==========

         .. bibliography::

   .. tab-item:: Markdown
      :sync: md

      .. code-block:: md

         ## References

         ```{bibliography}
         ```

No arguments are needed for the ``bibliography`` directive because it is automatically configured.

By default, all BibTeX files from lsst-texmf are available in your technote.

Adding local BibTeX entries
===========================

You can define your own BibTeX entries in a local bib file, such as :file:`local.bib`, when lsst-texmf is missing references.
Any ``*.bib`` file in the root of the technote repository is automatically included in the build.

Creating citations in text
==========================

You can add citations in your text using ``cite`` and related roles.
The ``cite`` roles takes the bibkey as the argument.

Author-year citations with cite
-------------------------------

The ``cite`` role adds a parenthetical inline citation like ``[Author et al., Year]``:

.. tab-set::
   :sync-group: markup

   .. tab-item:: RST
      :sync: rst

      .. code-block:: rst

         :cite:`RTN-095`

   .. tab-item:: Markdown
      :sync: md

      .. code-block:: md

         {cite}`RTN-095`

Multiple bibkeys can be included, separated by commas:

.. tab-set::
   :sync-group: markup

   .. tab-item:: RST
      :sync: rst

      .. code-block:: rst

         :cite:`bibkey1,bibkey2`

   .. tab-item:: Markdown
      :sync: md

      .. code-block:: md

         {cite}`bibkey1,bibkey2`

Textual citations with cite:t
-----------------------------

The ``cite:t`` role adds a textual citation like ``Author et al. (Year)``:

.. tab-set::
   :sync-group: markup

   .. tab-item:: RST
      :sync: rst

      .. code-block:: rst

         :cite:t:`RTN-095`

   .. tab-item:: Markdown
      :sync: md

      .. code-block:: md

         {cite:t}`RTN-095`

Specialized citation roles
--------------------------

The sphinxcontrib-bibtex extension also provides specialized citation roles for specific situations, such as listing authors or years, or including pre- or post-text inside a parenthetical citation.
See the `sphinxcontrib-bibtex documentation <https://sphinxcontrib-bibtex.readthedocs.io/en/latest/usage.html#roles-and-directives>`__ for details.

Refresh bib files from lsst-texmf
=================================

The lsst-texmf bib files are automatically downloaded and cached in the :file:`.technote` directory when your technote is built. You can refresh the cached files by deleting the :file:`.technote` directory and rebuilding your technote.

.. prompt::

   rm -rf .technote
   make html

You can also delete both the cache and the existing built HTML with:

.. prompt::

   make clean
