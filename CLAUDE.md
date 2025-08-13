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
pip install -e ".[technote,guide]" --group dev  # Install with all extras
```

### Testing and Quality Assurance
```bash
tox -e py-test-sphinx8      # Run tests with Sphinx 8.x
tox -e coverage-report      # Generate coverage report
tox -e typing-sphinx8       # Run mypy type checking
tox -e lint                 # Run linting (pre-commit hooks + prettier)
tox -e demo                 # Build demo technote projects (end-to-end test)
tox -e packaging            # Check PyPI packaging
```

### Documentation
```bash
tox -e docs                 # Build documentation
tox -e docs-lint            # Check documentation links
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

**Services** (`src/documenteer/services/`):
- `technoteauthor.py`: Author management for technotes
- `technotemigration.py`: Legacy technote migration logic

### Key Design Patterns

- **Configuration as Code**: Sphinx configurations are Python modules that can be imported
- **Pydantic Models**: TOML configuration validation using type-safe models
- **Extension Architecture**: Modular Sphinx extensions for specific Rubin/LSST needs
- **Theme Integration**: Tight integration with pydata-sphinx-theme and technote themes

### Testing Strategy

- Uses tox for multi-environment testing across Sphinx versions
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
