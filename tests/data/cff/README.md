# Vendored Citation File Format schema

`schema-1.2.0.json` is the Citation File Format 1.2.0 JSON Schema, copied
here verbatim so that `tests/services/technotecff_test.py` can validate the
`CITATION.cff` that `documenteer technote sync-cff` generates.

| | |
| --- | --- |
| Source | <https://raw.githubusercontent.com/citation-file-format/citation-file-format/1.2.0/schema.json> |
| Upstream repository | <https://github.com/citation-file-format/citation-file-format> |
| Version | 1.2.0 (released 2021-08-09) |
| Commit | `396f738fb025b1d8acdb02a56ffc923f95dc8999` |
| SHA-256 | `0b8d22140da702d766df318dcff3a91af2f39521298dcf36d76315fd99cc169b` |
| License | [CC BY 4.0](https://github.com/citation-file-format/citation-file-format/blob/1.2.0/LICENSE), Citation File Format contributors |

## Why it is vendored

The schema is copied rather than fetched because the test suite for the
citation work is offline and deterministic throughout: a test that reached
citation-file-format.github.io would fail in a sandboxed CI job and would
change meaning whenever upstream re-published the file.

Copying it is also what avoids depending on `cffconvert`, the reference
validator. `cffconvert` pins `jsonschema<4`, so adding it would downgrade
this project's environment from `jsonschema` 4.x — which `nbformat` and
therefore `myst-nb` resolve — to 3.2. Validating against the schema directly
with the `jsonschema` already in the environment gives the same coverage
without that constraint.

## Updating

Replace the file with a later release's `schema.json` verbatim — do not
hand-edit it — and update the version, commit, and checksum above:

```sh
curl -fsSL -o tests/data/cff/schema-1.2.0.json \
  https://raw.githubusercontent.com/citation-file-format/citation-file-format/1.2.0/schema.json
shasum -a 256 tests/data/cff/schema-1.2.0.json
```

A new CFF version also changes the `cff-version` that
`documenteer.services.technotecff` writes, so the two move together.
