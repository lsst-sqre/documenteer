.PHONY: help
help:
	@echo "Make command reference"
	@echo "  make init ........ (initialize for development)"

.PHONY: init
init:
	rm -rf .tox
	uv pip install --upgrade pre-commit tox tox-uv scriv
	uv pip install -e ".[technote,pipelines]" --group dev
	pre-commit install

.PHONY: clean
clean:
	rm -rf .tox
	rm -rf docs/_build
	rm -rf docs/dev/api/contents/*.rst
	make -C demo/rst-technote clean
