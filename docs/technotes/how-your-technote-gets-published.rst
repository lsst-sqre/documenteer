###########################################
How your technote gets published to the web
###########################################

Technotes are published onto the web through the process of pushing commits to GitHub.
This page explains that process in more detail.

The main website
================

Rubin technotes are published to the web on the ``lsst.io`` domain, with a dedicated subdomain that corresponds to the document's handle.
For example, if a document is assigned the handle ``DMTN-123``, it will be published to ``https://dmtn-123.lsst.io``.

By default, this main page corresponds to the latest build from the technote repository's ``main`` branch.

Views for other branches and tags
=================================

If you push a commit to a branch other than ``main``, or if you push a tag, the technote will be published to a different URL.
You can find a listing of these alternative editions of the technote at the ``/v`` URL path (or click the :guilabel:`View all versions` link in the left sidebar of the technote webpage).

How GitHub Actions builds and publishes the technote
====================================================

Technotes are built and published to the web by a GitHub Actions workflow.
By default, this workflow is the :file:`.github/workflows/ci.yaml` workflow.
You can view the status and logs for GitHub Actions workflows at the :guilabel:`Actions` tab of the technote repository.
For more information, see `GitHub's documentation on GitHub Actions <https://docs.github.com/en/actions>`__.

The default :file:`ci.yaml` workflow delegates to a reusable workflow in https://github.com/lsst-sqre/rubin-sphinx-technote-workflows.
By default, this workflow runs the ``make html`` command to build the technote.
