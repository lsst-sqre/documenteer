##########################################
Handling CSS, JavaScript, and image assets
##########################################

Documenteer uses webpack to compile CSS, JavaScript and image assets.
This page explains where asset sources are maintained, and how these assets are packaged with Documenteer.

Asset sources are maintained in Documenteer's repository in the ``src/assets`` directory.
Webpack compiles and installs these assets into the Documenteer package at ``src/documenteer/assets``.
These compiled assets are not committed in Git, but *are* included in the Python package via ``MANIFEST.in``.
Therefore the webpack build step (``npm run build``) *must* be run in any development and CI environment.

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
