##############################################################################
Including OpenAPI documentation for web applications (documenteer.ext.openapi)
##############################################################################

The HTTP interface for web applications is typically described using an OpenAPI specification.
FastAPI, the Python web framework for building web APIs automatically generates an OpenAPI specification from the application's code.
The `documenteer.ext.openapi` extension can call a function in your application to generate the OpenAPI specification and include it in the Sphinx documentation.
Then with the third-party `sphinxcontrib-redoc`_ extension, the OpenAPI specification can be rendered as an HTML page in your documentation site.

.. seealso::

   If you are using the :doc:`Rubin user guide </guides/index>` configuration (``documenteer[guide]``), the Redoc site and OpenAPI generator can be configured with the documenteer.toml file.
   See :doc:`/guides/openapi` for more details.

Usage guide
===========

These steps lead you through the basic steps for integrating OpenAPI-based documentation into the Sphinx documentation site for a FastAPI application using this extension and `sphinxcontrib-redoc`_.

1. Create a function to generate the OpenAPI docs
-------------------------------------------------

The first step is to create or identify a function that generates an OpenAPI specification for your application as a JSON-serialized string.
This function must be importable from the Sphinx build process.
For FastAPI applications, it may make sense to add this function to the :file:`main.py` module where the FastAPI application is defined:

.. code-block:: python
   :caption: src/main.py

   import json

   from fastapi import FastAPI
   from fastapi.openapi.utils import get_openapi


   app = FastAPI()


   def create_openapi() -> str:
       """Create the OpenAPI spec for static documentation."""
       spec = get_openapi(
           title=app.title,
           version=app.version,
           description=app.description,
           routes=app.routes,
       )
       return json.dumps(spec)


2. Add the Sphinx extensions
----------------------------

Add the ``"documenteer.ext.openapi"`` and ``"sphinxcontrib-redoc"`` extensions to the Sphinx :file:`conf.py` file:

.. code-block:: python
   :caption: docs/conf.py

   extensions = ["sphinxcontrib.redoc", "documenteer.ext.openapi", ...]

.. important::

   Ensure that the `sphinxcontrib-redoc`_ package is installed.
   If you are using the ``documenteer[guide]`` extra, then this package is already installed, see :doc:`/guides/index`.

3. Configure the OpenAPI generator function
-------------------------------------------

In the :file:`conf.py` file, use the :ref:`documenteer-openapi-generator-conf` configuration to specify the function that generates the OpenAPI specification:

.. code-block:: python
   :caption: docs/conf.py

   documenteer_openapi_generator = {
       "func": "squarebot.main:create_openapi",
   }
   documenteer_openapi_path = "_static/openapi.json"

Note how the value of the ``"func"`` key is a string that specifies the module and function name, separated by a colon.
In this case, the ``create_openapi`` function is importable from the ``squarebot.main`` Python namespace.

Note that the generator function can take positional and keyword arguments.
See the :ref:`documenteer-openapi-generator-conf` reference documentation for more details.

4. Configure the redoc extension
--------------------------------

The second set of configurations is for the `sphinxcontrib-redoc`_ extension.

.. code-block:: python
   :caption: docs/conf.py

   redoc = [
       {
           "name": "REST API",
           "page": "api",
           "spec": "_static/openapi.json",
           "embed": True,
           "opts": {"hide-hostname": True},
       }
   ]

The ``spec`` field is critical, and should match the value of ``documenteer_openapi_path``.

5. Add a stub page to the documentation
---------------------------------------

This step is optional, however it provides an improved reader experience.
The `sphinxcontrib-redoc`_ extension renders the OpenAPI spec into an HTML page, but this page isn't included in the Sphinx ``toctree``.
This means that the redoc-generated HTML page is not included in the navigation menu and can't be linked with the ``:doc:`` role.
A work-around for this is to add a stub file to the documentation site that is replaced by the `sphinxcontrib-redoc`_ extension.

Since the ``redoc`` configuration above has a ``page`` value of ``api``, the HTML file will be written to :file:`api.html`.
Therefore, the stub file should be :file:`api.rst`:

.. code-block:: rst
   :caption: docs/api.rst

   ########
   REST API
   ########

   This is a stub page for the API.

In the site's index page, add the API page, via the reStructuredText stub, to the ``toctree``:

.. code-block:: rst
   :caption: docs/index.rst

   .. toctree::

      api

Finally, build the Sphinx documentation.
When you navigate to the "REST API" page in the contents menu, you should see the rendered redoc-rendered OpenAPI documentation.

Reference
=========

Extension module
----------------

To use the extension, include ``"documenteer.ext.openapi"`` in the extensions list in :file:`conf.py`:

.. code-block:: python
   :caption: conf.py

   extensions = ["documenteer.ext.openapi", ...]

Configurations
--------------

Set these configurations in the Sphinx :file:`conf.py` file.


.. _documenteer-openapi-generator-conf:

documenteer\_openapi\_generator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This configuration specifies the function that can generate the OpenAPI specification as a JSON-serialized string.
Setting this configration also enables the extension.

The most basic form of this configuration is a `dict` with a ``"func"`` key.
The format of the value is ``{module}:{function}``.
For example, if the generator function is called ``create_openapi`` and located in the ``main.py`` module of the ``squarebot`` package/application, then the configuration would be:

.. code-block:: python
   :caption: conf.py

   documenteer_openapi_generator = {
       "func": "squarebot.main:create_openapi",
   }

If the generator function takes positional arguments, then they can be specified in a list under the ``"args"`` key:

.. code-block:: python
   :caption: conf.py

   documenteer_openapi_generator = {
       "func": "squarebot.main:create_openapi",
       "args": ["arg1", "arg2"],
   }

If the generator function takes keyword arguments, then they can be specified in a dictionary under the ``"kwargs"`` key:

.. code-block:: python
   :caption: conf.py

   documenteer_openapi_generator = {
       "func": "squarebot.main:create_openapi",
       "kwargs": {"kwarg1": "value1", "kwarg2": "value2"},
   }


.. _documenteer-openapi-path-conf:

documenteer\_openapi\_path
^^^^^^^^^^^^^^^^^^^^^^^^^^

This is the path, relative to the Sphinx :file:`conf.py` file, where the OpenAPI spec file is written.

If you are using the `sphinxcontrib-redoc`_ extension, this path should match the ``spec`` field in the ``redoc`` configuration.

.. code-block:: python
   :caption: conf.py

   documenteer_openapi_path = "_static/openapi.json"
   redoc = [
       {
           "title": "Example API",
           "page": "api",
           "spec": "_static/openapi.json",
           "embed": True,
       }
   ]
