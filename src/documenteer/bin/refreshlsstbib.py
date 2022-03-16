"""Command line executable to refresh lsst bib files."""

__all__ = ["run", "make_parser"]

import argparse
import logging
import os
import sys
import urllib

import requests

from ..version import __version__


def run():
    """Command line entrypoint for the ``refresh-lsst-bib`` program."""
    args = make_parser().parse_args()

    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if not args.verbose:
        # Manage third-party loggers
        req_logger = logging.getLogger("requests")
        req_logger.setLevel(logging.WARNING)

    logger = logging.getLogger("documenteer")

    logger.info("refresh-lsst-bib version {}".format(__version__))

    error_count = process_bib_files(args.dir)

    sys.exit(error_count)


def make_parser():
    """Create an argument parser for the ``refresh-lsst-bib`` program.

    Returns
    -------
    args : `argparse.ArgumentParser`
        ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="refresh-lsst-bib",
        description="Download LSST .bib bibliography files from the "
        "lsst-texmf GitHub repository.",
        epilog="Version {}".format(__version__),
    )
    parser.add_argument(
        "-d",
        "--dir",
        default=".",
        help="Directory to download bib files into. Default is the current "
        "working directory.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        default=False,
        help="Enable Verbose output (debug level logging)",
    )
    return parser


def process_bib_files(local_dir):
    """Run the refresh-lsst-bib program's logic: iterates through bib URLs,
    downloads the file from GitHub, and writes it to a local directory.

    Parameters
    ----------
    local_dir : `str`
        Directory to write bib files into.

    Returns
    -------
    error_count : `int`
        Number of download errors.
    """
    logger = logging.getLogger(__name__)

    # check the output directory exists
    if not os.path.isdir(local_dir):
        logger.error('Output directory "{}" does not exist'.format(local_dir))
        sys.exit(1)

    root_blob_url = (
        "https://raw.githubusercontent.com/lsst/lsst-texmf/"
        "master/texmf/bibtex/bib/"
    )
    bib_filenames = [
        "books.bib",
        "lsst-dm.bib",
        "lsst.bib",
        "refs.bib",
        "refs_ads.bib",
    ]

    error_count = 0
    for bib_filename in bib_filenames:
        url = urllib.parse.urljoin(root_blob_url, bib_filename)
        logger.info("Downloading {}".format(url))
        try:
            content = _get_content(url)
        except requests.HTTPError as e:
            logger.exception(str(e))
            logger.warning("Could not download {}".format(url))
            error_count += 1
            continue

        local_filename = os.path.join(local_dir, bib_filename)
        with open(local_filename, "w") as f:
            f.write(content)

    return error_count


def _get_content(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text
