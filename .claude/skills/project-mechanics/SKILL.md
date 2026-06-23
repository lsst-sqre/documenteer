---
name: project-mechanics
description: Project-specific build/test/lint/typing commands for this repo. Read this skill at the start of any phase that runs validation (`stoker-work`, `stoker-fixup`, `stoker-rebase`).
---

# Project mechanics

This file is the source of truth for how this repo runs tests, lint,
and type-checking. Profile-shipped phase skills read it at the start
of each phase and use the named commands verbatim.

## Test commands

- `focused_test`: `tox -e py-test-sphinx8 -- -k <test_name>` (posargs after `--` pass through to pytest, so you can also use `tox -e py-test-sphinx8 -- tests/foo_test.py::test_bar`)
- `complete_test`: `tox -e py-test-sphinx7,py-test-sphinx8`

## Lint

- `lint_touched`: `pre-commit run --files {files}`
- `lint_all`: `tox -e lint`

## Typing

- `typing`: `tox -e typing-sphinx8`

## Final validation

End-of-task validation runs `tox -e py-test-sphinx7,py-test-sphinx8` +
`tox -e lint` + `tox -e typing-sphinx8` in that order, in the
foreground, plus `tox -e demo` (end-to-end rst/md/ipynb demo technote
builds) and `tox -e docs` (Documenteer's own Sphinx docs build).

The full Python × Sphinx matrix (3.12/3.13 × Sphinx 7/8), `tox -e
docs-lint` (linkcheck), and `tox -e packaging` (build + twine check)
are CI's responsibility, not the in-iteration gate.

<!-- stoker-onboarded-from: github.com/lsst-sqre/rubin-stoker//profile@main
     prompt-hash: 348ec538f8f7f6fa42da3569d855eab629174668ef28ea225f8b37511daac9d4
     onboarded-at: 2026-06-23T21:19:20Z -->
