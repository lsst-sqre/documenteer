# Demo technote

```{abstract}
A *technote* is a web-native single page document that enables rapid technical communication within and across teams.
```

## Introduction

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Proin facilisis pharetra neque, at semper nulla mattis auctor. Proin semper mollis enim eget interdum. Mauris eleifend eget diam vitae bibendum. Praesent ut aliquet odio, sodales imperdiet nisi. Nam interdum imperdiet tortor sed fringilla. Maecenas efficitur mi sodales nulla commodo rutrum. Ut ornare diam quam, sed commodo turpis aliquam et. In nec enim consequat, suscipit tortor sit amet, luctus ante. Integer dictum augue diam, non pulvinar massa euismod in. Morbi viverra condimentum auctor. Nullam et metus mauris. Cras risus ex, porta sit amet nibh et, dapibus auctor leo.

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Proin facilisis pharetra neque, at semper nulla mattis auctor. Proin semper mollis enim eget interdum. Mauris eleifend eget diam vitae bibendum. Praesent ut aliquet odio, sodales imperdiet nisi. Nam interdum imperdiet tortor sed fringilla. Maecenas efficitur mi sodales nulla commodo rutrum. Ut ornare diam quam, sed commodo turpis aliquam et. In nec enim consequat, suscipit tortor sit amet, luctus ante. Integer dictum augue diam, non pulvinar massa euismod in. Morbi viverra condimentum auctor. Nullam et metus mauris. Cras risus ex, porta sit amet nibh et, dapibus auctor leo.

A parenthetical citation {cite:p}`SQR-083`. And a textual citation {cite:t}`SQR-083`.

This is `inline code`.


## Images and figures

A figure with a caption:

```{figure} https://placehold.co/1200x400

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed euismod, nisl quis molestie ultricies, nunc nisl aliquet nunc, quis aliquam nisl nunc eu nisl.
```

### Wide figures

A figure marked with the `technote-wide-content` class applied as a `figclass` option:

```{figure} https://placehold.co/1200x400
:figclass: technote-wide-content

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed euismod, nisl quis molestie ultricies, nunc nisl aliquet nunc, quis aliquam nisl nunc eu nisl.
```

### Tables

A table:

```{list-table}
:header-rows: 1

* - Column 1
  - Column 2
  - Column 3
* - Row 1
  - 1
  - 1
* - Row 2
  - 2
  - 2
* - Row 3
  - 3
  - 3
```

A table marked with the `technote-wide-content` class:

```{rst-class} technote-wide-content
```

```{list-table}
:header-rows: 1

* - Column 1
  - Column 2
  - Column 3
  - Column 4
  - Column 5
  - Column 6
  - Column 7
* - Row 1
  - lorem ipsum dolor sit amet consectetur adipiscing elit
  - lorem ipsum dolor
  - lorem ipsum dolor
  - 5
  - 6
  - Lorem ipsum
* - Row 2
  - 6
  - 7
  - 8
  - 9
  - 10
  - Lorem ipsum
```

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed euismod, nisl quis molestie ultricies, nunc nisl aliquet nunc, quis aliquam nisl nunc eu nisl.

### Code blocks

A regular code block:

```{code-block} python
print("Hello, world!")
```

And with a caption:

```{code-block} python
:caption: A code block with a caption

print("Hello, world!")
```

A wide code block without a caption:

```{rst-class} technote-wide-content
```

```{code-block} python
print("Hello, world! This is a code block. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed euismod, nisl quis molestie ultricies, nunc nisl aliquet nunc, quis aliquam nisl nunc eu nisl.")
```

A wide code block with a caption where the class is set externally:

```{rst-class} technote-wide-content
```

```{code-block} python
:caption: A wide code block. This is a long caption. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed euismod, nisl quis molestie ultricies, nunc nisl aliquet nunc, quis aliquam nisl nunc eu nisl.

print("Hello, world! This is a code block. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed euismod, nisl quis molestie ultricies, nunc nisl aliquet nunc, quis aliquam nisl nunc eu nisl.")
```

A code prompt:

```{prompt} bash
git add index.rst
```

## Admonitions

An admonition:

```{note}
This is a note. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed euismod, nisl quis molestie ultricies, nunc nisl aliquet nunc, quis aliquam nisl nunc eu nisl.

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed euismod, nisl quis molestie ultricies, nunc nisl aliquet nunc, quis aliquam nisl nunc eu nisl.
```

## Lists

A bulleted list:

- Item 1
- Item 2
- Item 3

A numbered list:

1. Item 1
2. Item 2
3. Item 3

A bulleted list with a nested numbered list:

- Item 1
  1. Item 1.1
  2. Item 1.2
- Item 2
- Item 3

A definition list:

term 1
  Definition 1
term 2
  Definition 2 Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed euismod, nisl quis molestie ultricies, nunc nisl aliquet nunc, quis aliquam nisl nunc eu nisl.

## Links

A link to [Rubin Observatory](https://www.rubinobservatory.org).

## Analysis

A flowchart made with Mermaid:

```{mermaid}
graph TD
   A[Square Rect] -- Link text --> B((Circle))
   A --> C(Round Rect)
   B --> D{Rhombus}
   C --> D
```

A diagram:

```{rst-class} technote-wide-content
```

```{diagrams} diagram.py
```

## Conclusion

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Proin facilisis pharetra neque, at semper nulla mattis auctor. Proin semper mollis enim eget interdum. Mauris eleifend eget diam vitae bibendum. Praesent ut aliquet odio, sodales imperdiet nisi. Nam interdum imperdiet tortor sed fringilla. Maecenas efficitur mi sodales nulla commodo rutrum. Ut ornare diam quam, sed commodo turpis aliquam et. In nec enim consequat, suscipit tortor sit amet, luctus ante. Integer dictum augue diam, non pulvinar massa euismod in. Morbi viverra condimentum auctor. Nullam et metus mauris. Cras risus ex, porta sit amet nibh et, dapibus auctor leo.

## References

```{bibliography}
```
