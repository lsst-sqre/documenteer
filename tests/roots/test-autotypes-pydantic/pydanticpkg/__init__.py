"""The package this test root documents.

``StampConfig`` is a Pydantic model carrying members that are *not* fields:
a method, a classmethod, and a property. This is the shape Rubin's
configuration models use (Safir's ``build_uws_config``, lsst.images'
``deserialize``), and those members are what autodoc-pydantic's model
documenter loses on Sphinx 9 without the compat shim.
"""

from __future__ import annotations

from pydantic import BaseModel

__all__ = ["StampConfig"]


class StampConfig(BaseModel):
    """A model whose useful API is not all fields."""

    label: str
    """The label stamped onto each record."""

    def serialize(self) -> str:
        """Render the configuration as a string.

        Returns
        -------
        str
            The serialized configuration.
        """
        return self.label

    @classmethod
    def deserialize(cls, data: str) -> StampConfig:
        """Build a configuration from a serialized string.

        Parameters
        ----------
        data
            The serialized configuration.

        Returns
        -------
        StampConfig
            The parsed configuration.
        """
        return cls(label=data)

    @property
    def shout(self) -> str:
        """The label, uppercased."""
        return self.label.upper()
