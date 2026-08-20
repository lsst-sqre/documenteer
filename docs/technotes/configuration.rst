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

.. _technote-conf-linkcheck:

Link-check settings
^^^^^^^^^^^^^^^^^^^

Technotes check their external links with the Ook_ link-check service: Documenteer's ``documenteer.ext.linkcheckservice`` extension replaces Sphinx's built-in linkcheck_ builder with one that submits the technote's links to the service and polls for the results.
Guides configure that builder through the ``[sphinx.linkcheck]`` table of a :file:`documenteer.toml` file, but technotes don't have that file, and :file:`technote.toml`'s schema belongs to the Technote_ package rather than to Documenteer.
:file:`conf.py` is therefore the supported way to override these settings in a technote.
Set any of them after the ``from documenteer.conf.technote import *`` line:

``documenteer_linkcheck_strict``
   Whether genuine link-check *service* problems fail the build.
   Default is ``False``: when the service is unreachable or the polling budget is exhausted, the builder emits a warning and the build finishes with a zero exit status.
   Set it to ``True`` to fail the build on those conditions instead.

   This setting gates only service *availability* problems.
   Links the service reports as broken always fail the build regardless of it, and a missing or rejected ``OOK_TOKEN`` never fails the build either: the builder falls back to Sphinx's built-in in-process linkcheck_ builder in every mode, so link checking still runs.

``documenteer_linkcheck_use_service``
   Whether to check links with the link-check service instead of Sphinx's built-in linkcheck_ builder.
   Default is ``True``.
   Set it to ``False`` as an escape hatch to restore the built-in builder, which checks each link in-process and doesn't require an Ook API token.

``documenteer_linkcheck_service_url``
   Base URL of the Ook_ API that hosts the link-check service.
   Default is ``"https://roundtable.lsst.cloud/ook"``.

``documenteer_linkcheck_poll_budget``
   Maximum time, in seconds, to wait for link-check results from the service.
   Default is ``300``.
   If the budget is exhausted before the service completes the check, the build emits a warning and continues — or fails, if ``documenteer_linkcheck_strict`` is ``True``.

For example, to make service problems fail the technote's build:

.. code-block:: python
   :caption: conf.py
   :emphasize-lines: 3

   from documenteer.conf.technote import *  # noqa: F401, F403

   documenteer_linkcheck_strict = True

.. note::

   The *origin base URL* — the base URL of the published technote that the submitted links are associated with — is derived rather than set.
   Documenteer takes it from :external+technote:ref:`[technote] canonical_url <toml-technote-canonical-url>` in :file:`technote.toml`, falling back to the technote's handle as ``https://<id>.lsst.io`` from :external+technote:ref:`[technote] id <toml-technote-id>`.
   Technotes therefore rarely need to set the ``documenteer_linkcheck_origin_base_url`` configuration value directly.
   If a build reports that no origin base URL is available for the link-check service, set ``canonical_url`` or ``id`` in :file:`technote.toml`, which is what that message asks for.

.. _technote-conf-intersphinx-cache:

Intersphinx inventory cache settings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Technotes prefetch their Intersphinx_ object inventories (:file:`objects.inv`) from the Ook_ inventory cache service: Documenteer's ``documenteer.ext.intersphinxcache`` extension downloads each one and points Sphinx at the local copy, so a technote build doesn't depend on third-party site availability.
A technote build therefore logs the same :ref:`inventory prefetch summary <guide-sphinx-intersphinx-cache-summary>` a user guide does, and gets the same notice when Ook reports that one of its configured inventory URLs has permanently moved.

The Intersphinx *projects* a technote links to aren't set here.
They live in the :external+technote:ref:`[technote.sphinx.intersphinx.projects] <toml-technote-sphinx-intersphinx-projects>` table of :file:`technote.toml` — which is also the table a permanent-redirect notice names when a URL you configure has moved.

The *cache* settings are a different matter.
Guides configure them through the ``[sphinx.intersphinx.cache]`` table of a :file:`documenteer.toml` file, but technotes don't have that file, and Documenteer adds no keys to :file:`technote.toml`, whose schema belongs to the Technote_ package rather than to Documenteer.
:file:`conf.py` is therefore the supported way to override these settings in a technote.
Set any of them after the ``from documenteer.conf.technote import *`` line:

``documenteer_intersphinx_cache_warn_on_permanent_redirect``
   Whether to report a permanently-moved inventory URL as a Sphinx warning rather than at the ``INFO`` log level.
   Default is ``False``, so a warnings-as-errors (``-W``) technote build never fails because a third party moved an inventory.
   Set it to ``True`` if you'd rather your build fail than carry a stale inventory URL.

   See :ref:`warn_on_permanent_redirect <guide-sphinx-intersphinx-cache-warn-on-permanent-redirect>` for what the notice says and what escalating it does — including the ``documenteer.intersphinx_permanent_redirect`` warning subtype that silences a move you already know about, while keeping the warning for every other inventory.

``documenteer_intersphinx_cache_use_service``
   Whether to prefetch inventories from the Ook_ inventory cache service.
   Default is ``True``.
   Set it to ``False`` as an escape hatch so Intersphinx_ fetches every inventory directly from its origin site.

``documenteer_intersphinx_cache_service_url``
   Base URL of the Ook_ API that hosts the inventory cache service.
   Default is ``"https://roundtable.lsst.cloud/ook"``.

``documenteer_intersphinx_cache_disk_cache_ttl``
   How long, in seconds, a prefetched inventory on disk is reused before Documenteer revalidates it with the service.
   Default is ``600`` (10 minutes).
   Set it to ``0`` to disable that fast path so every build revalidates with the service.

For example, to make a moved inventory URL fail the technote's build:

.. code-block:: python
   :caption: conf.py
   :emphasize-lines: 3

   from documenteer.conf.technote import *  # noqa: F401, F403

   documenteer_intersphinx_cache_warn_on_permanent_redirect = True

.. note::

   Prefetching needs a bearer token for the Ook_ API, read from the ``OOK_TOKEN`` environment variable.
   Without it the extension is a complete no-op and stock Intersphinx_ behavior is unchanged, so the technote still builds — there's simply no summary block in the log.

.. _technote-conf-source:

Configuration source reference
==============================

.. literalinclude:: ../../src/documenteer/conf/technote.py
