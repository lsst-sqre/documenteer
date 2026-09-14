"""Validation of a CITATION.cff document against the vendored CFF schema.

Both directions of Documenteer's CITATION.cff support are pinned against the
format itself: `tests/services/technotecff_test.py` validates the file
``documenteer technote sync-cff`` generates, and
`tests/storage/citationcff_test.py` validates the fixtures the reader is
tested against, so a fixture can never pin the reader's behavior on a file
CFF would reject.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date
from pathlib import Path

import jsonschema

__all__ = ["CFF_SCHEMA_PATH", "CFF_VALIDATOR", "assert_valid_cff"]

CFF_SCHEMA_PATH = Path(__file__).parent / "data" / "cff" / "schema-1.2.0.json"
"""The Citation File Format 1.2.0 JSON Schema, vendored verbatim.

:file:`tests/data/cff/README.md` records where it came from and why it is
kept here rather than fetched.
"""

CFF_VALIDATOR = jsonschema.Draft7Validator(
    json.loads(CFF_SCHEMA_PATH.read_text(encoding="utf-8")),
    format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER,
)
"""The validator built from that schema.

The format checker is what turns ``2026-02-30`` — a date the schema's own
pattern accepts — into a failure; every format CFF uses is checked by
``jsonschema`` itself, with no further dependency.
"""


def assert_valid_cff(document: object) -> None:
    """Assert that a parsed CITATION.cff satisfies CFF 1.2.0.

    The document is validated against the vendored schema, so a value of the
    wrong type, a malformed date, a value outside an enum, and a key CFF does
    not define are all caught — not merely a missing required key.

    cffconvert, the reference validator, is deliberately not a test
    dependency: it pins ``jsonschema<4``, so adding it would downgrade the
    ``jsonschema`` the rest of the environment resolves — Jupyter's notebook
    reader among it. Since cffconvert validates against this very schema,
    reading it directly gives up nothing.
    """
    errors = sorted(
        CFF_VALIDATOR.iter_errors(_as_json(document)),
        key=lambda error: error.json_path,
    )
    assert not errors, "\n".join(
        f"{error.json_path}: {error.message}" for error in errors
    )


def _as_json(value: object) -> object:
    """Render a YAML-parsed document as the JSON the schema validates.

    PyYAML resolves an unquoted ``2026-08-24`` to a `datetime.date`, which
    JSON has no notion of. The schema says so itself, asking implementers to
    cast YAML date objects to strings before validating. A
    `~datetime.datetime` casts the same way, and to a string the ``date``
    pattern rejects — which is the right answer, because CFF dates are days.
    """
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _as_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_as_json(item) for item in value]
    return value
