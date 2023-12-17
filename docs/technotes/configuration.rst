############################
Configuring the Sphinx build
############################

Documenteer provides centralized configuration for technotes.
To use these configurations, you must first install Documenteer with the "technote" extra, see :ref:`installation guide <install-technotes>`.

.. _technote-basic-conf:

Basic configuration
===================

To use Documenteer's configuration in a Sphinx technote project, the Sphinx :file:`conf.py` file must contain the following import:

.. code-block:: python
   :caption: conf.py

   from documenteer.conf.technote import *

This configuration uses content from the :file:`technote.toml` file, also in the technote repository, along with defaults in Documenteer to configure the technote build.

Customizing the Sphinx build
============================

Most technote projects don't need to customize the Sphinx build beyond the defaults provided by Documenteer.
If you do need to customize the build, there are two ways to do so: :file:`technote.toml` and :file:`conf.py`.

With technote.toml
------------------

The recommended way to customize the build, where possible, is to through the :external+technote:ref:`[technote.sphinx] <toml-technote-sphinx>` table in the :file:`technote.toml` file.
Some key configurations provided through :file:`technote.toml` include:

- Adding additional Sphinx extensions (see :doc:`extensions`)
- Adding projects for Intersphinx (:external+technote:ref:`[technote.sphinx.intersphinx] <toml-technote-sphinx-intersphinx>`)
- Setting the exemptions for the link check (:external+technote:ref:`[technote.sphinx.linkcheck] <toml-technote-sphinx-linkcheck>`)
- Setting the "nitpick" mode and exemptions for warning on build issues

.. seealso::

   `Configuring the Sphinx build <https://technote.lsst.io/user-guide/configure-sphinx.html>`__, from the Technote package documentation.

With conf.py
------------

If :file:`technote.toml` does not provide the configuration you need, you can customize the Sphinx build by adding additional lines of Python to your :file:`conf.py` file.
Any lines added to the :file:`conf.py` file can override the configuration provided by Documenteer, or set new Sphinx configurations.
The existing configurations provided by Documenteer are shown in :ref:`technote-conf-source`, below.

.. seealso::

   :external+technote:ref:`direct-sphinx-conf`, from the Technote package documentation.

.. _technote-conf-source:

Configuration source reference
==============================

.. literalinclude:: ../../src/documenteer/conf/technote.py
