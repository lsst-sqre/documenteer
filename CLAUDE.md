# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Documenteer is a Python package that provides Sphinx documentation tools, extensions, and configurations for Rubin Observatory/LSST projects. It supports two main documentation types:
- **User guides**: Complete documentation sites using pydata-sphinx-theme
- **Technotes**: Single-document technical notes using the technote theme

## Development Commands

### Setup and Installation
```bash
make init                    # Initialize development environment
uv sync --extra technote --extra guide --group dev --group nox --group lint  # Install with all extras
```

Tasks are run with [nox](https://nox.thea.codes/) (via [nox-uv](https://github.com/cthoyt/nox-uv)). Invoke nox through uv so the runner is provisioned automatically: `uv run --only-group=nox nox -s <session>`. The `test`, `typing`, and `demo` sessions are parametrized over both Python (3.12, 3.13) and Sphinx (8, 9, dev), so their session IDs carry both factors, e.g. `nox -s "test-3.13(sphinx='8')"`. uv furnishes the requested interpreter on demand. Bare `nox` runs a lean default set (3.13 × Sphinx 8/9); run `nox -l` to see the exact IDs.

### Testing and Quality Assurance
```bash
nox -s "test-3.13(sphinx='8')"   # Run tests on Python 3.13 with Sphinx 8.x (sphinx also '9'/'dev'; python also '3.12')
nox -s test                      # Run the full Python × Sphinx grid
nox -s coverage-report           # Generate coverage report
nox -s "typing-3.13(sphinx='8')" # Run mypy type checking
nox -s lint                      # Run linting (prek hooks, incl. prettier)
nox -s "demo-3.13(sphinx='9')"   # Demo technote build (e2e smoke test; full grid via 'nox -s demo')
nox -s packaging                 # Check PyPI packaging
```

Coverage is opt-in via `DOCUMENTEER_COVERAGE=1`, which runs the test suite under `coverage` and auto-combines a report. CI sets `DOCUMENTEER_COVERAGE_NO_COMBINE=1` in each matrix cell so it uploads raw `.coverage.*` data for a central `coverage-combine` job to merge once across the whole matrix.

### Documentation
```bash
nox -s docs                 # Build documentation
nox -s docs-linkcheck       # Check documentation links
```

### Cleanup
```bash
make clean                  # Remove build artifacts
```

## Architecture

### Core Components

**Configuration System** (`src/documenteer/conf/`):
- `guide.py`: Sphinx configuration preset for user guides
- `technote.py`: Sphinx configuration preset for technotes
- `_toml.py`: TOML-based configuration models using Pydantic
- Uses pydata-sphinx-theme for guides, [technote](https://github.com/lsst-sqre/technote) package for technotes

**Sphinx Extensions** (`src/documenteer/ext/`):
- `jira.py`: JIRA ticket references
- `lsstdocushare.py`: LSST DocuShare document links
- `openapi.py`: OpenAPI documentation integration
- `githubbibcache.py`: GitHub-based bibliography caching
- `bibtex.py`: Enhanced BibTeX support
- `remotecodeblock.py`: Remote code inclusion
- `mockcoderefs.py`: Mock code references for testing
- `redoc.py`: Redoc integration for HTTP API documentation
- `robots.py`: robots.txt generation

**CLI Tools** (`src/documenteer/cli.py`):
- `technote add-author`: Add authors to technote.toml from authordb
- `technote sync-authors`: Sync author info from central database
- `technote migrate`: Migrate legacy technotes to modern format
- `technote validate`: Validate a technote's metadata, structure, and content (stable TN0xx/TN1xx/TN2xx check codes)

**Services** (`src/documenteer/services/`):
- `technoteauthor.py`: Author management for technotes
- `technotemigration.py`: Legacy technote migration logic

### Key Design Patterns

- **Configuration as Code**: Sphinx configurations are Python modules that can be imported
- **Pydantic Models**: TOML configuration validation using type-safe models
- **Extension Architecture**: Modular Sphinx extensions for specific Rubin/LSST needs
- **Theme Integration**: Tight integration with pydata-sphinx-theme and technote themes

### Testing Strategy

- Uses nox (nox-uv) for multi-environment testing across Sphinx versions
- Sphinx test roots in `tests/roots/` for extension testing
- Coverage reporting with branch coverage
- Type checking with mypy
- Pre-commit hooks for code quality

### Code Style

- Follows ruff formatting (run lint command to automatically format)
- Numpydoc docstrings with types omitted (Sphinx documentation uses type annotations)

### Asset Management

Static assets are managed in `src/documenteer/assets/` including:
- Custom CSS and SCSS for Rubin branding
- JavaScript enhancements
- Favicon and logo assets
- Font files (Source Sans Pro)

Built assets are compiled using webpack with PostCSS processing.
