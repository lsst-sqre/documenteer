##########################################
Handling CSS, JavaScript, and image assets
##########################################

Documenteer uses webpack to compile CSS, JavaScript and image assets.
This page explains where asset sources are maintained, and how these assets are packaged with Documenteer.

Asset sources are maintained in Documenteer's repository in the ``src/assets`` directory.
Webpack compiles and installs these assets into the Documenteer package at ``src/documenteer/assets``.
These compiled assets are not committed in Git, but *are* included in the Python package via ``MANIFEST.in``.
Therefore the webpack build step (``npm run build``) *must* be run in any development and CI environment.

.. _theme-assets-github-packages:

Authenticating npm to GitHub Packages
=====================================

Documenteer's npm dependencies include the private ``@lsst-sqre/rubin-style-dictionary`` package, which is published to GitHub Packages rather than the public npm registry.
The repository's ``.npmrc`` points the ``@lsst-sqre`` scope at ``https://npm.pkg.github.com/``, so ``npm install`` must authenticate to GitHub Packages before it can download that package.

GitHub Packages' npm registry **only accepts a classic personal access token (PAT)**; fine-grained tokens are rejected with a ``403`` ``permission_denied`` ("token does not match expected scopes") error.
Create a classic PAT with **only** the ``read:packages`` scope at https://github.com/settings/tokens, and — because ``lsst-sqre`` enforces SAML single sign-on — authorize the token for the ``lsst-sqre`` organization.

Outside a dev container
-----------------------

To build the assets directly on your machine, add the token to your user ``~/.npmrc``:

.. code-block:: ini

   //npm.pkg.github.com/:_authToken=<your classic read:packages PAT>

The dev container and GitHub Codespaces configurations instead read the token from a ``NPM_PKG_TOKEN`` environment variable and write that same ``~/.npmrc`` line automatically during ``postCreateCommand``.
A local (Docker Desktop) dev container inherits ``NPM_PKG_TOKEN`` from the shell that launches it, so export it before opening the container.

In GitHub Codespaces
--------------------

Codespaces does not have access to your local environment, so it cannot inherit ``NPM_PKG_TOKEN`` from your shell.
The token that Codespaces provisions automatically (``GITHUB_TOKEN``) can't be used either: it is scoped to this repository and cannot read ``@lsst-sqre/rubin-style-dictionary``, which is published from a different repository.

Instead, provide the token as a **personal** (account-level) `Codespaces secret`_, so it is private to *your* codespaces and is not shared on the repository:

#. Create a classic ``read:packages`` PAT as described above (authorized for ``lsst-sqre`` SSO).
#. Go to https://github.com/settings/codespaces → :guilabel:`Codespaces secrets` → :guilabel:`New secret`.
#. Name it ``NPM_PKG_TOKEN``, paste the token, and grant it access to the ``lsst-sqre/documenteer`` repository.

Or, equivalently, with the GitHub CLI:

.. code-block:: sh

   gh secret set NPM_PKG_TOKEN --user --app codespaces --repos lsst-sqre/documenteer

Each developer sets their own secret; nothing needs to be configured on the repository itself.
The next codespace you create on this repository will pick up the token and authenticate ``npm install`` during ``postCreateCommand``.
(An existing codespace needs to be rebuilt to pick up a newly-added secret.)

.. _Codespaces secret: https://docs.github.com/en/codespaces/managing-your-codespaces/managing-your-account-specific-secrets-for-github-codespaces

.. Source assets:
.. src/assets
.. node_modules/@lsst-sqre/rubin-style-dictionary/assets
..
.. Build tooling:
.. webpack.config.js
..
.. Packaged assets:
.. src/documenteer/assets
.. src/documenteer/assets/scripts
.. src/documenteer/assets/styles
.. src/documenteer/assets/rsd-assets
..
.. Sphinx configuration:
.. ``get_assets_path``
