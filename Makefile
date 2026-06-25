.PHONY: help
help:
	@echo "Make command reference"
	@echo "  make init ........ (initialize for development)"
	@echo "  make clean ....... (clean up build artifacts)"
	@echo "  make update-deps . (update dependencies and prek hooks)"

.PHONY: init
init:
	uv sync --extra technote --extra guide --group dev --group nox --group lint
	uv run prek install

.PHONY: clean
clean:
	rm -rf .nox
	rm -rf docs/_build
	rm -rf docs/dev/api/contents/*.rst
	make -C demo/rst-technote clean

.PHONY: update-deps
update-deps:
	uv lock --upgrade
	uv run --only-group=lint prek autoupdate
