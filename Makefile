.PHONY: help
help:
	@echo "Make command reference"
	@echo "  make init ........ (initialize for development)"

.PHONY: init
init:
	rm -rf .tox
	pip install -e ".[technote,pipelines]" --group dev
	pip install -U tox pre-commit scriv
	pre-commit install

.PHONY: clean
clean:
	rm -rf .tox
	rm -rf docs/_build
	rm -rf docs/dev/api/contents/*.rst
	make -C demo/rst-technote clean
