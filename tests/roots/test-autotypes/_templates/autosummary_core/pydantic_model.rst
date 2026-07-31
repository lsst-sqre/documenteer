{# Verbatim copy of gafaelfawr's automodapi template override, kept for
   provenance. Jinja comments are stripped before rendering, so this note
   never reaches the generated rst.

   In this test root automodsumm does consume the template. In the real
   world it is inert: the guide preset never registers autodoc-pydantic,
   so ``objtype`` is never ``pydantic_model`` and gafaelfawr never renders
   this file. The ConfigDict docstring leak this test root reproduces comes
   from plain ``autoclass`` with ``:inherited-members:``-style rendering --
   the explicit ``.. autoclass:: autotypespkg.StampSettings`` in index.rst
   is the actual reproduction. #}
{% if referencefile %}
.. include:: {{ referencefile }}
{% endif %}

{{ objname }}
{{ underline }}

.. currentmodule:: {{ module }}

.. auto{{ objtype }}:: {{ objname }}
   :inherited-members: BaseModel
