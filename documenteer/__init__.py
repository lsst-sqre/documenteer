__all__ = ('__version__',)

from pkg_resources import get_distribution, DistributionNotFound


try:
    __version__ = get_distribution('documenteer').version
except DistributionNotFound:
    # package is not installed
    __version__ = 'unknown'
