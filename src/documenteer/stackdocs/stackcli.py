"""Implements the ``stack-docs`` CLI for stack documentation builds.
"""

__all__ = ("main",)

import logging
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

import click

from .build import build_stack_docs
from .doxygentag import get_tag_entity_names
from .rootdiscovery import discover_conf_py_directory

# Add -h as a help shortcut option
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-d",
    "--dir",
    "root_project_dir",
    type=click.Path(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True
    ),
    default=".",
    help="Root Sphinx project directory. You don't need to set this argument "
    "explicitly as long as the current working directory is the "
    "main documentation repo (``pipelines_lsst_io`` for example) or a "
    "subdirectory of it.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output (debug-level logging).",
)
@click.version_option()
@click.pass_context
def main(ctx, root_project_dir, verbose):
    """stack-docs is a CLI for building LSST Stack documentation, such as
    pipelines.lsst.io.

    This command should be run on the "main" documentation repository, namely
    https://github.com/lsst/pipelines_lsst_io.

    The stack-docs command replaces the usual Makefile and sphinx-build system
    for Sphinx projects. This dedicated tool provide subcommands that are
    engineered specifically for building the ``pipelines_lsst_io`` project.

    The key commands provided by stack-docs are:

    - ``stack-docs build``: compile the pipelines.lsst.io site from the
      ``pipelines_lsst_io`` repository and linked packages.

    - ``stack-docs clean``: removes build products. Use this command to
      clear the build cache.

    See also: package-docs, a tool for building previews of package
    documentation.

    For more information about stack-docs, see https://documenteer.lsst.io.
    """
    root_project_dir = discover_conf_py_directory(root_project_dir)

    # Subcommands should use the click.pass_obj decorator to get this
    # ctx.obj object as the first argument.
    ctx.obj = {"root_project_dir": root_project_dir, "verbose": verbose}

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
@click.option(
    "-s",
    "--skip",
    multiple=True,
    help="A module (e.g. ``lsst.afw.geom`` or package (``afw``) name to "
    "exclude from the documentation. Provide multiple -s options to skip "
    "multiple names.",
)
@click.option(
    "--enable-doxygen-conf/--disable-doxygen-conf",
    help="Toggle creating a Doxygen configuration.",
    default=True,
)
@click.option(
    "--enable-doxygen/--disable-doxygen",
    help="Toggle running a Doxygen build.",
    default=True,
)
@click.option(
    "--enable-symlinks/--disable-symlinks",
    help=(
        "Toggle symlinking package documentation directories (disable for "
        "debugging only)."
    ),
    default=True,
)
@click.option(
    "--enable-sphinx/--disable-sphinx",
    help="Toggle running a Sphinx build.",
    default=True,
)
@click.option(
    "--use-doxygen-conf-in/--use-doxygen-conf",
    help=(
        "Use doxygen.conf.in files in packages rather than the "
        "sconsUtils-generated doxygen.conf files."
    ),
    default=True,
)
@click.option(
    "--doxygen-conf",
    "doxygen_conf_defaults_path",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    default=None,
    help=(
        "Path to a Doxygen configuration file that provides defaults. This "
        "file is referenced by the finalized Doxygen configuration with the "
        "@INCLUDE_PATH tag. Defaults to a doxygen configuration built into "
        "Documenteer."
    ),
)
@click.option(
    "--dox",
    multiple=True,
    help=(
        "Run Doxygen on only the packages explicitly listed, rather than "
        "automatically discovering set up packages."
    ),
)
@click.option(
    "--skip-dox",
    multiple=True,
    help=("Skip running Doxygen on these packages."),
)
@click.pass_context
def build(
    ctx,
    skip,
    enable_doxygen_conf,
    enable_doxygen,
    enable_symlinks,
    enable_sphinx,
    use_doxygen_conf_in,
    doxygen_conf_defaults_path,
    dox,
    skip_dox,
):
    """Build documentation as HTML.

    This command performs these steps:

    1. Removes any existing symlinks in the ``modules``, ``packages``, and
       ``_static`` directories.

    2. Finds packages set up by EUPS that have Sphinx-enabled doc/ directories
       and links their module and package directories into the
       ``pipelines_lsst_io`` repository. The ``doc/manifest.yaml`` file in
       each package is what defines the package and module documentation
       directories for each package.

    3. Run a single, monolithic Sphinx build on the ``pipelines_lsst_io``
       repository and linked packages.

    By default, the build site is located in the ``_build/html`` directory
    of the ``pipelines_lsst_io`` repository.

    To peek inside the build process, see the ``documenteer.stackdocs.build``
    APIs.
    """
    if doxygen_conf_defaults_path is not None:
        _doxygen_conf_defaults_path = Path(doxygen_conf_defaults_path)
    else:
        _doxygen_conf_defaults_path = None

    return_code = build_stack_docs(
        ctx.obj["root_project_dir"],
        skipped_names=skip,
        prefer_doxygen_conf_in=use_doxygen_conf_in,
        doxygen_conf_defaults_path=_doxygen_conf_defaults_path,
        enable_doxygen_conf=enable_doxygen_conf,
        enable_doxygen=enable_doxygen,
        enable_package_links=enable_symlinks,
        enable_sphinx=enable_sphinx,
        select_doxygen_packages=dox,
        skip_doxygen_packages=skip_dox,
    )
    if return_code > 0:
        sys.exit(return_code)


@main.command()
@click.pass_context
def clean(ctx):
    """Clean Sphinx build products.

    Use this command to clean out build products after a failed build, or
    in preparation for running a build from a clean state.

    This command removes the following directories from the
    ``pipelines_lsst_io`` directory:

    - ``_build`` (the Sphinx build itself)
    - ``modules`` (symlinks to the module doc directories of Stack packages)
    - ``packages`` (symlinks to the package doc directories of Stack packages)
    - ``py-api`` (pages created by automodapi for the Python API reference)
    - ``_doxygen`` (the Doxygen build)
    """
    logger = logging.getLogger(__name__)

    dirnames = ["py-api", "_build", "modules", "packages", "_doxygen"]
    dirnames = [
        os.path.join(ctx.obj["root_project_dir"], dirname)
        for dirname in dirnames
    ]
    for dirname in dirnames:
        if os.path.isdir(dirname):
            shutil.rmtree(dirname)
            logger.debug("Cleaned up %r", dirname)
        else:
            logger.debug("Did not clean up %r (missing)", dirname)


@main.command()
@click.option(
    "-t",
    "--type",
    "api_types",
    multiple=True,
    type=click.Choice(
        [
            "namespace",
            "struct",
            "class",
            "file",
            "define",
            "group",
            "variable",
            "typedef",
            "enumeration",
            "function",
        ]
    ),
    help=(
        "Type of documentation to list. Omit to list all API types. Provide "
        'multiple arguments to list several API types. "class" includes both '
        "classes and their methods."
    ),
)
@click.option(
    "-p",
    "--pattern",
    type=str,
    help=("Regular expression pattern to filter API names."),
)
@click.option(
    "--escape/--no-escape",
    default=True,
    help=("Escape the name so it can be used in reStructuredText (default)."),
)
@click.pass_context
def listcc(
    ctx: Any, api_types: Sequence[str], pattern: Optional[str], escape: bool
) -> None:
    """List C++ API names available in the Doxygen tag file for cross-linking.

    To make a cross-link from a reStructuredText file or Python docstring, use
    the syntax::

        :lsstcc:`{{name}}`

    Example usage::

        stack-docs listcc -t class -t function -p lsst::afw::table
    """
    tag_path = os.path.join(
        ctx.obj["root_project_dir"], "_doxygen", "doxygen.tag"
    )

    if pattern:
        p = re.compile(pattern)

    if not api_types:
        api_types = [
            "namespace",
            "struct",
            "class",
            "file",
            "define",
            "group",
            "variable",
            "typedef",
            "enumeration",
            "function",
        ]
    entities = get_tag_entity_names(tag_path=tag_path, kinds=api_types)
    for name in entities:
        if pattern:
            if not p.search(name):
                continue
        if escape:
            print(name.replace("<", r"\<").replace(">", r"\>"))
        else:
            print(name)
