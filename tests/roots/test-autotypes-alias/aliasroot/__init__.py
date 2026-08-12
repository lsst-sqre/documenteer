"""The top-level root a documented package and an external one share.

``lsst.images`` (documented) and ``lsst.resources`` (not) sit under the
``lsst`` root this way. Sharing the root is what puts the external
package's modules inside the typing registry's scan, while leaving them
outside every documented module prefix — the two halves of the gate the
plain-alias degrade applies.

This package itself is documented nowhere, so it contributes no module
prefix of its own.
"""

from __future__ import annotations
