### Bug fixes

- `documenteer.ext.autotypes` no longer emits `RemovedInSphinx10Warning: The tuple interface for _InventoryItem objects is deprecated` when it resolves a reference through its intersphinx fallback. The extension now reads the `uri` attribute of an inventory item on Sphinx 8.2 and later, and indexes the item as a tuple only on Sphinx 8.0 and 8.1, where inventory items are plain tuples.
