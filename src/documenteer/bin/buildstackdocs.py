"""build-stack-docs command-line application."""

__all__ = ["run_build_cli"]

import argparse
import logging
import os
import sys

from ..stackdocs.build import build_stack_docs
from ..version import __version__


def run_build_cli():
    """Command line entrypoint for the ``build-stack-docs`` program."""
    args = parse_args()

    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    logger = logging.getLogger("documenteer")

    logger.info("build-stack-docs version {0}".format(__version__))

    return_code = build_stack_docs(
        args.root_project_dir, enable_doxygen_conf=False, enable_doxygen=False
    )
    if return_code == 0:
        logger.info("build-stack-docs succeeded")
        sys.exit(0)
    else:
        logger.error("Sphinx errored: code {0:d}".format(return_code))
        sys.exit(1)


def parse_args():
    """Create an argument parser for the ``build-stack-docs`` program.

    Returns
    -------
    args : `argparse.Namespace`
        Parsed argument object.
    """
    parser = argparse.ArgumentParser(
        description="Build a Sphinx documentation site for an EUPS stack, "
        "such as pipelines.lsst.io.",
        epilog="Version {0}".format(__version__),
    )
    parser.add_argument(
        "-d",
        "--dir",
        dest="root_project_dir",
        default=os.getcwd(),
        help="Root Sphinx project directory",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        default=False,
        help="Enable Verbose output (debug level logging)",
    )
    return parser.parse_args()
