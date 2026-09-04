"""Reading a technote's metadata and content through a Sphinx build."""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from docutils import nodes
    from technote.metadata.model import TechnoteMetadata

__all__ = [
    "CONTENT_FILENAMES",
    "TECHNOTE_EXTRA_HINT",
    "TechnoteDocument",
    "TechnoteReadError",
    "read_technote",
]

CONTENT_FILENAMES = ("index.rst", "index.md", "index.ipynb")
"""The names a technote's root document may have, in the order Sphinx
resolves them.
"""

TECHNOTE_EXTRA_HINT = (
    "Reading a technote needs the technote extra. Install "
    "documenteer[technote]."
)
"""What to do about a missing ``technote`` package.

Both commands that read a technote — ``sync-cff`` and ``lint`` — run the
document through Sphinx, so both need the extra. Saying which extra to
install is the whole of the fix, and the message is shared so the two
commands say it the same way.
"""

_OFFLINE_OVERRIDES: dict[str, Any] = {
    # Reading the document resolves no cross-references, so no inventory
    # needs fetching. Sphinx applies a non-string override as-is, which is
    # what lets a mapping be emptied here at all.
    "intersphinx_mapping": {},
    # Documenteer's technote preset fetches lsst-texmf's bibfiles at
    # config-inited. The read needs no bibliography, and a technote author
    # on a plane should still be able to lint.
    "documenteer_bibfile_github_repos": [],
    # A notebook technote is read for its markup. Executing it would run
    # arbitrary code, take arbitrarily long, and change nothing this read
    # looks at.
    "nb_execution_mode": "off",
}
"""Configuration the read forces, whatever the technote's conf.py says.

Each entry names a configuration value belonging to an extension that a
technote *may* not load, in which case Sphinx logs that the override names
an unknown value into the discarded warning stream and carries on.
"""

_CONFIG_MODULES = ("documenteer.conf.technote", "technote.sphinxconf")
"""The modules a technote's conf.py imports its Sphinx settings from.

Both compute their values — the parsed ``technote.toml``, the extension list,
the exclude patterns — once, at import, from the current directory. Python
imports a module once per process, so a second technote read in the same
process would otherwise be handed the *first* technote's settings, and, worse,
would leave them behind for anything else in the process that builds a
technote. `_isolated_technote_config` gives each read its own import of them
and puts back whatever was there before.
"""


class TechnoteReadError(Exception):
    """Raised when a technote's document cannot be read.

    Carries the diagnosis in its message — Sphinx's own, where Sphinx
    produced one — so a command can report the condition rather than a
    traceback.
    """


@dataclass(frozen=True)
class TechnoteDocument:
    """A technote as its own Sphinx build sees it.

    Parameters
    ----------
    metadata
        The technote's metadata, with the title resolved the way the
        published page resolves it: from ``[technote] title`` when the file
        declares one, and otherwise from the document's H1.
    doctree
        The root document's parsed doctree.

    Notes
    -----
    ``metadata.date_updated`` is not the date ``technote.toml`` declares: the
    technote package defaults an undeclared ``date_updated`` to the moment of
    the build. A caller that needs the *declared* date — as CITATION.cff
    generation does, since a date that changes every run would make the
    generated file differ from itself — must read ``technote.toml`` rather
    than take it from here.
    """

    metadata: TechnoteMetadata
    doctree: nodes.document

    @property
    def title(self) -> str | None:
        """The technote's resolved title, or `None` if it has none."""
        return self.metadata.title or None


def read_technote(root_dir: Path) -> TechnoteDocument:
    """Read a technote's document with Sphinx and return what it says.

    The technote is built with the ``dummy`` builder, which runs Sphinx's
    read phase and writes nothing. That is deliberately the technote's *own*
    build — its ``conf.py``, its extensions, its markup — so that the title
    and abstract this reports are the ones the published page carries, rather
    than a second opinion from a parser Documenteer would have to maintain
    alongside Sphinx.

    Parameters
    ----------
    root_dir
        The technote's directory: the one holding ``technote.toml``,
        ``conf.py``, and the ``index`` content file.

    Returns
    -------
    `TechnoteDocument`
        The technote's metadata and the root document's doctree.

    Raises
    ------
    TechnoteReadError
        Raised if the ``technote`` extra is not installed, if the directory
        is not a technote Sphinx can configure, or if the build's read phase
        fails. The message names the condition, Sphinx's own words included.
    """
    factory, resolve_title = _load_technote()

    toml_path = root_dir / "technote.toml"
    if not toml_path.is_file():
        raise TechnoteReadError(
            f"No technote.toml found in {root_dir}, so there is no technote "
            "to read."
        )
    if not (root_dir / "conf.py").is_file():
        raise TechnoteReadError(
            f"No conf.py found in {root_dir}, so Sphinx cannot read the "
            "technote. A technote is built by Sphinx and needs one."
        )
    if not any((root_dir / name).is_file() for name in CONTENT_FILENAMES):
        # Answered here rather than left to Sphinx, which reports a missing
        # root document by embedding the technote package's traceback in its
        # message. The condition is one sentence; the traceback is not.
        listing = ", ".join(CONTENT_FILENAMES)
        raise TechnoteReadError(
            f"No content file ({listing}) found in {root_dir}, so there is "
            "no document to read."
        )

    doctree = _read_doctree(root_dir)

    try:
        factory.parse_toml(toml_path.read_text(encoding="utf-8"))
        metadata = factory.load_metadata()
    except Exception as e:
        raise TechnoteReadError(
            f"Could not read the metadata in {toml_path}: {e}"
        ) from e

    if not metadata.title:
        # An empty title is how the technote package says technote.toml
        # declares none, which is the normal case: `technote migrate` never
        # writes one. The document's own H1 is then the title, and is what
        # the built page publishes.
        metadata.title = resolve_title(doctree) or ""

    return TechnoteDocument(metadata=metadata, doctree=doctree)


def _load_technote() -> tuple[Any, Any]:
    """Import the pieces of the technote package the read needs.

    Imported here rather than at module scope so that importing this module
    — which ``documenteer.cli`` does at start-up — does not require the
    ``technote`` extra. A command that actually reads a technote does.
    """
    try:
        from technote.ext.metadata import resolve_title  # noqa: PLC0415
        from technote.factory import Factory  # noqa: PLC0415
    except ImportError as e:
        raise TechnoteReadError(TECHNOTE_EXTRA_HINT) from e
    return Factory(), resolve_title


@contextmanager
def _isolated_technote_config() -> Iterator[None]:
    """Give the enclosed Sphinx build its own import of the config modules.

    Each module in `_CONFIG_MODULES` is dropped from the import cache on the
    way in, so the ``conf.py`` this build executes computes its settings from
    *this* technote, and restored on the way out, so the read leaves the
    process's import state exactly as it found it.
    """
    saved: dict[str, ModuleType] = {}
    for name in _CONFIG_MODULES:
        module = sys.modules.pop(name, None)
        if module is not None:
            saved[name] = module
    try:
        yield
    finally:
        for name in _CONFIG_MODULES:
            sys.modules.pop(name, None)
        for name, module in saved.items():
            sys.modules[name] = module
            # Re-importing the module also rebound it as an attribute of its
            # parent package, so the parent has to be put back too or a later
            # `documenteer.conf.technote` attribute access answers with this
            # read's module rather than the restored one.
            parent_name, _, attribute = name.rpartition(".")
            parent = sys.modules.get(parent_name)
            if parent is not None:
                setattr(parent, attribute, module)


def _read_doctree(root_dir: Path) -> nodes.document:
    """Run the technote's read phase and return the root document's doctree.

    The build's output and doctree caches go to a temporary directory that is
    removed on the way out, so reading a technote never writes into the
    repository it reads — a lint run in a clean checkout leaves it clean.
    """
    from sphinx.application import Sphinx  # noqa: PLC0415

    with (
        tempfile.TemporaryDirectory(prefix="documenteer-read-") as build_dir,
        _isolated_technote_config(),
    ):
        build = Path(build_dir)
        try:
            app = Sphinx(
                srcdir=str(root_dir),
                confdir=str(root_dir),
                outdir=str(build / "out"),
                doctreedir=str(build / "doctrees"),
                buildername="dummy",
                # Sphinx writes its progress and its warnings to these
                # streams rather than to the terminal, so the read is quiet
                # whatever the technote's own build is noisy about. A warning
                # is not this reader's business: the lint rules report what
                # the *document* says, and Sphinx reports its own warnings
                # when the technote is built for real.
                status=StringIO(),
                warning=StringIO(),
                # Nothing is cached between runs, so nothing stale can be
                # read back.
                freshenv=True,
                confoverrides=dict(_OFFLINE_OVERRIDES),
            )
            app.build()
            return app.env.get_doctree(app.config.root_doc)
        except TechnoteReadError:
            raise
        except Exception as e:
            # Sphinx raises a family of errors (SphinxError and its
            # subclasses, ExtensionError) and a parser can raise anything at
            # all — nbformat's NotJSONError for a corrupt notebook, say. All
            # of them mean the same thing to a caller: this technote could
            # not be read, and here is why.
            raise TechnoteReadError(str(e) or type(e).__name__) from e
