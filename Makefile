.PHONY: help
help:
	@echo "Make command reference"
	@echo "  make init ........ (initialize for development)"

.PHONY: init
init:
	rm -rf .tox
	pip install -e ".[dev,technote,pipelines]"
	pip install tox tox-pyenv pre-commit
	pre-commit install
