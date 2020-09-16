"""Implements the ``package-docs`` CLI for single-package documentation builds
in the LSST Stack.
"""

__all__ = ("main",)

import logging
import os
import shutil
import sys

import click

from ..sphinxrunner import run_sphinx
from .rootdiscovery import discover_package_doc_dir

# Add -h as a help shortcut option
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-d",
    "--dir",
    "root_dir",
    type=click.Path(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True
    ),
    default=".",
    help="Root Sphinx doc/ directory. You don't need to set this argument "
    "explicitly as long as the current working directory is any of:\n\n"
    "- the root of the package\n"
    "- the doc/ directory\n"
    "- a subdirectory of doc/\n",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output (debug-level logging).",
)
@click.version_option()
@click.pass_context
def main(ctx, root_dir, verbose):
    """package-docs is a CLI for building single-package previews of
    documentation in the LSST Stack.

    Use package-docs during development to quickly preview your documentation
    and docstrings.

    .. warning::

       Using package-docs to compile standalone documentation for a single
       package will generate warnings related to missing references. This is
       normal because the full documentation set is not built in the mode.
       Before shipping revised documentation for a package, always make sure
       cross-package references work by doing a full-site build either locally
       with the stack-docs CLI or the site's Jenkins job.

    The key commands provided by package-docs are:

    - ``package-docs build``: compile the package's documentation.
    - ``package-docs clean``: removes documentation build products from a
      package.
    """
    root_dir = discover_package_doc_dir(root_dir)

    # Subcommands should use the click.pass_obj decorator to get this
    # ctx.obj object as the first argument.
    ctx.obj = {"root_dir": root_dir, "verbose": verbose}

    # Set up application logging. This ensures that only documenteer's
    # logger is activated. If necessary, we can add other app's loggers too.
    if verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logger = logging.getLogger("documenteer")
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(log_level)


@main.command()
@click.argument("topic", default=None, required=False, nargs=1)
@click.pass_context
def help(ctx, topic, **kw):
    """Show help for any command."""
    # The help command implementation is taken from
    # https://www.burgundywall.com/post/having-click-help-subcommand
    if topic is None:
        click.echo(ctx.parent.get_help())
    else:
        click.echo(main.commands[topic].get_help(ctx))


@main.command()
@click.pass_context
def build(ctx):
    """Build documentation as HTML.

    The build HTML site is located in the ``doc/_build/html`` directory
    of the package.
    """
    return_code = run_sphinx(ctx.obj["root_dir"])
    if return_code > 0:
        sys.exit(return_code)


@main.command()
@click.pass_context
def clean(ctx):
    """Clean Sphinx build products.

    Use this command to clean out build products after a failed build, or
    in preparation for running a build from a clean state.

    This command removes the following directories from the package's doc/
    directory:

    - ``_build`` (the Sphinx build itself)
    - ``py-api`` (pages created by automodapi for the Python API reference)
    """
    logger = logging.getLogger(__name__)

    dirnames = ["py-api", "_build"]
    dirnames = [
        os.path.join(ctx.obj["root_dir"], dirname) for dirname in dirnames
    ]
    for dirname in dirnames:
        if os.path.isdir(dirname):
            shutil.rmtree(dirname)
            logger.debug("Cleaned up %r", dirname)
        else:
            logger.debug("Did not clean up %r (missing)", dirname)
