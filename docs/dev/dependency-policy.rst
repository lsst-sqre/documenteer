.. _dependency-policy:

#########################
Dependency support policy
#########################

Documenteer sets the minimum supported versions of Python and its core documentation dependencies according to `SPEC 0`_, the Scientific Python ecosystem's recommendation for dropping support for old releases.
This page documents that policy and how it maps onto Documenteer's own version numbers.

Supported versions
==================

Following `SPEC 0`_:

- **Python** is supported for three years after a minor release.
  Documenteer raises its ``requires-python`` floor once a Python version is more than three years old.

- **Core documentation dependencies** — Sphinx, pydata-sphinx-theme, Technote, and docutils — are supported for two years after a release.
  Documenteer raises its minimum requirement for one of these packages once a version is more than two years old.

Raising a floor lets Documenteer adopt newer features of these dependencies and keeps the supported matrix small enough to test thoroughly.

How floor changes map to releases
=================================

Raising a dependency floor — including dropping support for a Python or Sphinx version — does not change Documenteer's *own* public interface, so it ships as a **minor** release (for example, ``2.4`` to ``2.5``).
Every floor change is announced in the change log under the *Backwards-incompatible changes* heading.

A **major** release is reserved for breaking changes to Documenteer's own interface:

- the public Python API, including the configuration presets |documenteer.conf.guide| and ``documenteer.conf.technote``;
- the ``documenteer`` command-line interface;
- the |documenteer.toml| configuration schema.

In other words, you can upgrade across Documenteer minor releases expecting only that the supported Python and dependency versions may have moved forward, while your own ``conf.py`` and ``documenteer.toml`` keep working.

.. _SPEC 0: https://scientific-python.org/specs/spec-0000/
