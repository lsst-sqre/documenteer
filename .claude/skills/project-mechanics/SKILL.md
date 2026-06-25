---
name: project-mechanics
description: Project-specific build/test/lint/typing commands for this repo. Read this skill at the start of any phase that runs validation (`stoker-work`, `stoker-fixup`, `stoker-rebase`).
---

# Project mechanics

This file is the source of truth for how this repo runs tests, lint,
and type-checking. Profile-shipped phase skills read it at the start
of each phase and use the named commands verbatim.

Tasks run through nox (via nox-uv). Invoke nox through uv so the runner
group is provisioned automatically: `uv run --only-group=nox nox ...`.
The `test` and `typing` sessions are parametrized over Sphinx versions,
so their session names carry the parameter, e.g. `test(sphinx='8')`.

## Test commands

- `focused_test`: `uv run --only-group=nox nox -s "test(sphinx='8')" -- -k <test_name>` (posargs after `--` pass through to pytest, so you can also use `uv run --only-group=nox nox -s "test(sphinx='8')" -- tests/foo_test.py::test_bar`)
- `complete_test`: `uv run --only-group=nox nox -s "test(sphinx='7')" "test(sphinx='8')"`

## Coverage

Coverage is opt-in. The `test` session runs plain pytest by default, so no
`.coverage*` files are written during normal validation. To collect coverage
and print a combined report across the test sessions, set the
`DOCUMENTEER_COVERAGE` environment variable, e.g.
`DOCUMENTEER_COVERAGE=1 uv run --only-group=nox nox -s "test(sphinx='7')" "test(sphinx='8')"`.
The `coverage-report` session (combine + report) is triggered automatically
via `session.notify` when `DOCUMENTEER_COVERAGE` is set, and can also be run
directly to re-display the last combined report.

## Lint

- `lint_touched`: `uv run --only-group=lint pre-commit run --files {files}`
- `lint_all`: `uv run --only-group=nox nox -s lint`

## Typing

- `typing`: `uv run --only-group=nox nox -s "typing(sphinx='8')"`

## Final validation

End-of-task validation runs `uv run --only-group=nox nox -s
"test(sphinx='7')" "test(sphinx='8')"` + `uv run --only-group=nox nox -s
lint` + `uv run --only-group=nox nox -s "typing(sphinx='8')"` in that
order, in the foreground, plus `uv run --only-group=nox nox -s demo`
(end-to-end rst/md/ipynb demo technote builds) and `uv run
--only-group=nox nox -s docs` (Documenteer's own Sphinx docs build).

The full Python × Sphinx matrix (3.12/3.13 × Sphinx 7/8), `nox -s
docs-linkcheck` (linkcheck), and `nox -s packaging` (build + twine
check) are CI's responsibility, not the in-iteration gate.

<!-- stoker-onboarded-from: github.com/lsst-sqre/rubin-stoker//profile@main
     prompt-hash: 348ec538f8f7f6fa42da3569d855eab629174668ef28ea225f8b37511daac9d4
     onboarded-at: 2026-06-23T21:19:20Z -->
