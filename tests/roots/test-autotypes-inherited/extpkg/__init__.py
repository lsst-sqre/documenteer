"""A stand-in for an external package documented in its own project.

This package is deliberately *not* documented by the test root, so its
objects are external to the build: the only way to link one is through the
stub intersphinx inventory that :file:`conf.py` writes.
"""

from __future__ import annotations

__all__ = ["Formatter", "Packer"]


class Formatter:
    """A base formatter, documented in the external project."""

    def to_bytes(self) -> bytes:
        """Serialize the dataset to bytes.

        Returns
        -------
        bytes
            The serialized form of the dataset.
        """
        raise NotImplementedError

    def write_local_file(self, path: str) -> None:
        """Write the dataset to a local file.

        The default implementation delegates to `to_bytes`; subclasses
        that cannot produce a byte stream override this method instead.
        That bare reference is written in *this* module's context, but
        ``autodoc_inherit_docstrings`` renders it on the overriding
        subclass's page in another package.

        Parameters
        ----------
        path
            Where to write the dataset.
        """
        raise NotImplementedError


class Packer:
    """Another external class that also defines ``to_bytes``.

    Its presence makes the terminal name ``to_bytes`` ambiguous in the
    stub inventory, so only the fully-qualified name reconstructed from
    the documented class's MRO can resolve the inherited reference.
    """

    def to_bytes(self) -> bytes:
        """Serialize the packed data to bytes.

        Returns
        -------
        bytes
            The serialized form of the packed data.
        """
        raise NotImplementedError
