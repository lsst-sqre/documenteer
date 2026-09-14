### Other changes

- A user guide that marks no `[[project.citations]]` entry `self` now relates its parts to itself in both directions, the way one that marks an entry `self` does. The site-wide JSON-LD block names an entry that claims a `page` under `hasPart`, and the claimed page's own block points back with an `isPartOf` reference to the same schema.org `WebSite` node that block is about — the site's title and base URL, and no identifier, since such a site publishes no DOI of its own. A consumer arriving at either end can therefore reach the other whether or not the site publishes a DOI.
