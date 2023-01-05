#############################
Handling Jinja HTML templates
#############################

Directory structure
===================

Jinja templates for HTML themes are located within the ``src/documenteer/templates`` directory.
The subdirectories correspond to the Sphinx themes that these templates override:

- ``pydata`` customizes the pydata-sphinx-theme_ for Rubin user guides.
- ``technote`` customizes the Technote_ theme templates for Rubin technotes.

The Sphinx configurations presets configure these template directories with Sphinx's ``templates_path`` configuration variable, in combination with the `documenteer.conf.get_template_dir` helper:

.. code-block:: python

   templates_path = [get_template_dir("technote")]

The file layout within the ``pydata`` and ``technote`` templates directories match those of the source pydata-sphinx-theme_ and Technote_ repositories.
This enables Documenteer to override template components in the parent themes by including a template file with the same name.

pydata layout
-------------

The ``layout.html`` template is the base HTML page template.

See the `pydata-sphinx-theme templates directory on GitHub <https://github.com/pydata/pydata-sphinx-theme/tree/main/src/pydata_sphinx_theme/theme/pydata_sphinx_theme>`__ for other template files to implement.

technote layout
---------------

The ``sections`` directory correspond to the major layout areas, such as the sidebars, headers, footers, and content area.
Override these templates to change the contents of different sections, and to include different *components*.

The ``components`` directory contains specific components, such the logo, source control metadata info, etc.
Sections are composed of components.

See the `technote templates directory on GitHub <https://github.com/lsst-sqre/technote/tree/main/src/technote/theme>`__ to see the existing section and component templates that can be extended or overridden by Documenteer.
