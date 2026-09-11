"""Reports a `~pydantic.ValidationError` in the vocabulary of the TOML file
that was validated.

Pydantic addresses a problem in the model it validated and words it for
whoever wrote that model: a dotted, zero-based location such as
``project.citations.1.date``, a ``Value error,`` prefix, a truncated dump of
the rejected input, and a link to pydantic's error documentation. None of it
names anything a documentation author wrote.

This module translates such an error back into the file. It walks the same
location against the models it came from and accumulates the address in TOML's
own vocabulary — the table, the position of the entry counted from one, the
field — then states each problem as the sentence its validator raised. It is
written against any pydantic model rooted at a TOML file, so
:file:`documenteer.toml` and :file:`technote.toml` report their problems the
same way even though only one of the two models is Documenteer's.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import UnionType
from typing import Any, Self, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError
from pydantic_core import ErrorDetails

__all__ = ["format_validation_error"]


_ARRAY_ITEM_NOUNS = {
    "citations": "entry",
    "authors": "author",
}
"""What one item of an array is called, keyed by the array's name.

An array has no names of its own, so an error inside one is addressed by
position — and the word in front of the number is what tells an author which
array they are being pointed at. ``entry`` is the word
``documenteer.conf._toml`` already uses of a ``[[project.citations]]`` entry,
so both paths address the same entry the same way. An array not named here
falls back to ``item``.
"""


def _classify_annotation(
    annotation: Any,
) -> tuple[str, type[BaseModel] | None]:
    """Say what a model field is in the vocabulary of TOML — a ``table``, an
    ``array``, a ``mapping``, or a ``scalar`` — along with the model its
    contents are, when it has one.

    An optional field is classified as what it is when it is written, since
    leaving it out is how a TOML file says ``None``.
    """
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        members = [
            member
            for member in get_args(annotation)
            if member is not type(None)
        ]
        if not members:
            return "scalar", None
        return _classify_annotation(members[0])
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return "table", annotation
    if origin in (list, tuple, set, frozenset):
        args = [arg for arg in get_args(annotation) if arg is not Ellipsis]
        item = args[0] if args else None
        if isinstance(item, type) and issubclass(item, BaseModel):
            return "array", item
        return "array", None
    if origin is dict:
        parameters = get_args(annotation)
        value = parameters[-1] if parameters else None
        if isinstance(value, type) and issubclass(value, BaseModel):
            return "mapping", value
        return "mapping", None
    return "scalar", None


class _ErrorAddress:
    """The place in a TOML file that a pydantic error location points at.

    Pydantic addresses an error in the model it validated: a dotted,
    zero-based path such as ``project.citations.1.date``, sometimes ending in
    the name of the union member that rejected the value. An author reading
    that has to translate it back into the file they wrote. This walks the
    same location against the models and accumulates the address in the
    file's own vocabulary instead — the table the error is in, the position of
    the entry counted from one, and the field — stopping at the first segment
    that names no part of the file, which is how a union member's tag is
    dropped.
    """

    def __init__(self, root: type[BaseModel]) -> None:
        self._table: list[str] = []
        self._trail: list[str] = []
        self._field: str | None = None
        self._is_array_of_tables = False
        self._cursor: type[BaseModel] | None = root
        self._noun = "item"
        self._at_item = False
        self._rejected_by: type[BaseModel] | None = None

    @property
    def rejected_by(self) -> type[BaseModel] | None:
        """The model that rejected a key the address ends in, when the walk
        ended at one, and `None` otherwise.

        It is what lets the error say which keys the table does accept, since
        that is a property of the model rather than of the error.
        """
        return self._rejected_by

    def walk(self, loc: tuple[int | str, ...]) -> Self:
        """Follow an error location as far as it names the file."""
        segments = list(loc)
        index = 0
        while index < len(segments):
            following = (
                segments[index + 1] if index + 1 < len(segments) else None
            )
            consumed = self._step(segments[index], following)
            if consumed == 0:
                break
            index += consumed
        return self

    def label(self, value: Any) -> Self:
        """Name the array entry the error is about by its ``label``, when the
        rejected input is an entry that has one.

        The position of an entry says where it is; its label says which one it
        is, and is what its author called it. Only an error about a whole
        entry is labelled, since that is the only one whose input is the entry
        itself.
        """
        if self._field is not None or not self._trail:
            return self
        if isinstance(value, Mapping):
            label = value.get("label")
            if isinstance(label, str) and label:
                self._trail[-1] += f" (label {label!r})"
        return self

    def __str__(self) -> str:
        head = ""
        if self._table:
            path = ".".join(self._table)
            head = f"[[{path}]]" if self._is_array_of_tables else f"[{path}]"
        rest = ", ".join(self._trail)
        if self._field is not None:
            rest = f"{rest}, field {self._field}" if rest else self._field
        return f"{head} {rest}".strip()

    def _step(self, segment: int | str, following: int | str | None) -> int:
        """Take the next segment of the location, returning how many segments
        it consumed — zero when it names no part of the file, which ends the
        walk.
        """
        if isinstance(segment, int):
            return self._enter_item(segment)
        if self._cursor is None or segment not in self._cursor.model_fields:
            return self._name_rejected_key(segment)
        kind, member = _classify_annotation(
            self._cursor.model_fields[segment].annotation
        )
        if kind == "table":
            # A table is part of the address whether or not the error reaches
            # inside it, so `[project.python]` names the table that is missing
            # as readily as the one a field of failed.
            self._enter_table(segment, member)
            return 1
        if kind == "mapping" and isinstance(following, str):
            # A mapping of scalars is a table in TOML, and its key is written
            # in that table rather than being an index into anything.
            self._enter_table(segment, member)
            self._field = following
            return 2
        if (
            kind == "array"
            and member is not None
            and isinstance(following, int)
        ):
            self._enter_array(segment, member)
            return 1
        return self._name_field(segment, kind, following)

    def _enter_table(self, name: str, member: type[BaseModel] | None) -> None:
        (self._trail or self._table).append(name)
        self._cursor = member
        self._field = None

    def _enter_array(self, name: str, member: type[BaseModel]) -> None:
        # Only an array *of tables* is written `[[...]]`, and only the
        # outermost one heads the address: an array nested inside an entry is
        # named by the noun its own items carry.
        if not self._trail:
            self._table.append(name)
            self._is_array_of_tables = True
        self._noun = _ARRAY_ITEM_NOUNS.get(name, "item")
        self._cursor = member
        self._at_item = True
        self._field = None

    def _enter_item(self, position: int) -> int:
        if not self._at_item:
            return 0
        self._trail.append(f"{self._noun} #{position + 1}")
        self._at_item = False
        self._field = None
        return 1

    def _name_rejected_key(self, segment: str) -> int:
        """Take a segment that names no field of the model, which is part of
        the file only when the model forbids extra keys.

        Such a segment is normally pydantic's own — the tag it names a union
        member by — and ends the walk rather than being printed as though the
        author had written it. A table that forbids extra keys is the case
        where the author *did* write it, and the key is the whole of what the
        error is about, so it is named.
        """
        cursor = self._cursor
        if cursor is None or cursor.model_config.get("extra") != "forbid":
            return 0
        self._rejected_by = cursor
        self._cursor = None
        self._field = segment
        return 1

    def _name_field(
        self, name: str, kind: str, following: int | str | None
    ) -> int:
        self._cursor = None
        if kind == "array" and isinstance(following, int):
            # An array of scalars is written inline, so an element of it is a
            # position within the field rather than a table of its own.
            item = _ARRAY_ITEM_NOUNS.get(name, "item")
            self._field = f"{name} {item} #{following + 1}"
            return 2
        self._field = name
        return 1


def _describe_error(
    error: ErrorDetails, *, rejected_by: type[BaseModel] | None = None
) -> str:
    """State one validation problem in a sentence an author can act on.

    A validator's own `ValueError` is that sentence: it was written for the
    person who wrote the file, so it is used verbatim, without the ``Value
    error,`` prefix pydantic puts in front of it. Everything pydantic rejects
    on its own — a missing field, a value of the wrong type, a value outside
    an enumeration — comes with a short message of its own, which is used as
    it stands unless it names a model class. Neither the rejected input nor
    pydantic's documentation link is printed: the input is in the file the
    author is being sent back to, and the link explains the model rather than
    the file.

    Parameters
    ----------
    error
        One problem, as pydantic reports it.
    rejected_by
        The model that rejected an unaccepted key, when that is what the
        error is (see `_ErrorAddress.rejected_by`). A table with a closed set
        of keys can say what they are, which turns "not permitted" into the
        list the author is choosing from.
    """
    ctx = error.get("ctx") or {}
    cause = ctx.get("error")
    if error["type"] in {"value_error", "assertion_error"} and cause:
        return str(cause).strip()
    if error["type"] == "model_type":
        # Pydantic names the model class the table is read into, which is an
        # implementation detail and not anything written in the file. TOML
        # calls it a table.
        return "Input should be a table"
    if error["type"] == "extra_forbidden" and rejected_by is not None:
        accepted = ", ".join(
            field.alias or name
            for name, field in rejected_by.model_fields.items()
        )
        return f"No such key. This table accepts {accepted}."
    return str(error["msg"]).strip()


def format_validation_error(
    error: ValidationError, *, root: type[BaseModel], source: str
) -> str:
    """Report everything wrong with a TOML file, in the file's own terms.

    Parameters
    ----------
    error
        The validation failure, as pydantic raised it.
    root
        The model the file is validated into, which the error's locations are
        walked against to be translated into addresses in the file.
    source
        The name of the file, such as ``documenteer.toml``, which the report
        opens by naming.

    Returns
    -------
    str
        The report: the file, then one paragraph per problem, each addressing
        a place in the file and saying what is wrong there. Several problems
        are numbered and counted, so they can be fixed in one pass rather than
        one build each.
    """
    problems: list[tuple[str, str]] = []
    for detail in error.errors(include_url=False):
        place = (
            _ErrorAddress(root).walk(detail["loc"]).label(detail.get("input"))
        )
        problems.append(
            (
                str(place),
                _describe_error(detail, rejected_by=place.rejected_by),
            )
        )
    if len(problems) == 1:
        address, message = problems[0]
        body = f"{address}\n  {message}" if address else message
        return f"Configuration error in {source}:\n\n{body}"
    paragraphs = [
        f"{number}. {address}\n   {message}"
        if address
        else f"{number}. {message}"
        for number, (address, message) in enumerate(problems, start=1)
    ]
    header = f"{len(problems)} configuration errors in {source}:"
    return "\n\n".join([header, *paragraphs])
