<!-- Delete the sections that don't apply -->

### Backwards-incompatible changes

-

### New features

- Improved and extended the nitpick ignore configurations for both user guides and technotes. The new configuration engine uses a common set of utility functions to generate the ignore patterns. Second, Documenteer makes better use of regex patterns to ignore linking issues to APIs that are not documented with Sphinx, such as `fastapi`, `httpx`, and `pydantic`. This should reduce the number of nitpick warnings in user guides and technotes, and generally reduce the need for manual nitpick ignores in projects.

### Bug fixes

-

### Other changes

-
