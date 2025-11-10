### Other changes

- Fixed pytest configuration in `pyproject.toml` by consolidating conflicting `[tool.pytest]` and `[tool.pytest.ini_options]` sections into a single `[tool.pytest.ini_options]` section. This resolves an error that prevented tests from running.
