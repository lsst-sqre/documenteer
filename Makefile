.PHONY: help
help:
	@echo "Make command reference"
	@echo "  make init ........ (initialize for development)"

.PHONY: init
init:
	rm -rf .tox
	pip install -e ".[dev,guide,technote,pipelines]"
	pip install tox pre-commit scriv
	pre-commit install

.PHONY: clean
clean:
	rm -rf .tox
	rm -rf docs/_build
	rm -rf docs/dev/api/contents/*.rst
	make -C demo/rst-technote clean
