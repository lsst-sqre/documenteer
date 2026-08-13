"""The package this test root documents.

``auth_dependency`` is a module-level instance of a ``__call__``-defining
class — the shape Safir's FastAPI dependency-injection helpers use. Autodoc
classifies it as a ``data`` object, but the instance is callable and carries
annotations (its class annotates ``header_name``), so
sphinx-autodoc-typehints computes a signature for it anyway.
"""

from __future__ import annotations

__all__ = ["AuthDependency", "auth_dependency"]


class AuthDependency:
    """A callable dependency, instantiated once at module scope."""

    header_name: str = "X-Auth-Request-User"
    """The request header the username is read from."""

    async def __call__(self, token: str) -> str:
        """Return the username the token authenticates."""
        return token


auth_dependency = AuthDependency()
"""The process-wide dependency instance."""
