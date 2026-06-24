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

To build the assets outside a dev container, add the token to your user ``~/.npmrc``:

.. code-block:: ini

   //npm.pkg.github.com/:_authToken=<your classic read:packages PAT>

The dev container and GitHub Codespaces configurations instead read the token from a ``NPM_PKG_TOKEN`` environment variable and write that same ``~/.npmrc`` line automatically during ``postCreateCommand``.
In a Codespace, provide the token as a `Codespaces secret`_ named ``NPM_PKG_TOKEN``; the token that Codespaces provisions automatically is scoped to this repository and cannot read a package published from another repository.

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
