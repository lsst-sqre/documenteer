#######################################################
Using the rst epilog for common links and substitutions
#######################################################

Sphinx provides a feature for dynamically including content at the bottom of every reStructuredText page, called the `rst_epilog`_ in the standard Sphinx configuration.
This epilog is a great place to put standard Sphinx substitutions and link targets so that they can be reused throughout a documentation project.

In the Rubin user guide configuration, you can configure a standard reStructuredText file to serve as the content for `rst_epilog`_ with the :ref:`sphinx.rst_epilog_file <guide-project-rst-epilog-file>` configuration:

.. code-block:: toml
   :caption: documenteer.toml

    [sphinx]
    rst_epilog_file = "_rst_epilog.rst"

Then in the referenced :file:`_rst_epilog.rst` file, include links and substitutions:

.. code-block:: rst
   :caption: _rst_epilog.rst

   .. _Astropy Project: https://www.astropy.org

   .. |required| replace:: :bdg-primary-line:`Required`
   .. |optional| replace:: :bdg-secondary-line:`Optional`

Now on any page, you can use those links and substitutions:

.. code-block:: rst

   |required|

   `Astropy Project`_
