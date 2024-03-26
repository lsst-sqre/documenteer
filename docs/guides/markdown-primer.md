# Using Markdown syntax in Rubin Observatory documentation

Rubin Observatory user guides use [MyST-Parser](https://myst-parser.readthedocs.io/en/latest/) to support Markdown syntax in addition to reStructuredText.
This page explains the specific Markdown syntax that is supported in Rubin Observatory's Sphinx documentation and how it relates to the reStructuredText syntax you may already be familiar with for Sphinx documentation.
If you are {doc}`including Jupyter Notebooks in your documentation <including-notebooks>`, you can also use this Markdown syntax in your prose cells.

## Mixing Markdown and reStructuredText

The default content markup for Rubin Observatory documentation is reStructuredText (rst).
You can also elect to use Markdown syntax for your documentation content.
In the same user guide, you have both Markdown (``.md``) and reStructuredText (``.rst``) files.

```{note}
It's a good idea to check with your team to see if they have a preference for using Markdown or reStructuredText.
Having a consistent style across your documentation will make it easier for your team to maintain and update the content.
```

## Roles

Roles add semantic meaning to text.
Roles are *inline*, so they work at the word or phrase level (as opposed to directives, which apply to paragraph blocks).

In Markdown, roles are indicated by curly braces around the role name, followed by the content in single back ticks.
Examples of `ref` and `doc` roles:

```{code-block} markdown
{ref}`text <link-target>`

{doc}`index`
```

## Directives

Directives are block-level formatting elements.
Examples include admonitions like `note`, content blocks like `code-block`, and content-generators like `toctree`.
In Markdown, directives use the triple-backtick *code fence* syntax, with the directive name following the opening backticks in curly braces:

````{code-block} markdown
```{note}
Content of the note.
```
````

Fields in directives are indicated by colons around in the field name, followed by the value (just like in reStructuredText):

````{code-block} markdown
```{toctree}
:maxdepth: 2

page-one
page-two
```
````

## More resources

For more information and examples of the Markdown syntax supported in Rubin Observatory documentation, see the [MyST-Parser documentation](https://myst-parser.readthedocs.io/en/latest/).
