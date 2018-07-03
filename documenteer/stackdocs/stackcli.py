"""Implements the ``stack-docs`` CLI for stack documentation builds.
"""

__all__ = ('main',)

import logging
import os
import shutil
import sys
import click

from .build import build_stack_docs
from .rootdiscovery import discover_conf_py_directory


# Add -h as a help shortcut option
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    '-d', '--dir', 'root_project_dir',
    type=click.Path(exists=True, file_okay=False, dir_okay=True,
                    resolve_path=True),
    default='.',
    help="Root Sphinx project directory. You don't need to set this argument "
         "explicitly as long as the current working directory is the "
         "main documentation repo (pipelines_lsst_io for example) or a "
         "subdirectory of it."
)
@click.option(
    '-v', '--verbose',
    is_flag=True,
    help='Enable verbose output (debug-level logging)'
)
@click.version_option()
@click.pass_context
def main(ctx, root_project_dir, verbose):
    """stack-docs is a CLI for building LSST Stack documentation, such as
    pipelines.lsst.io.
    """
    root_project_dir = discover_conf_py_directory(root_project_dir)

    # Subcommands should use the click.pass_obj decorator to get this
    # ctx.obj object as the first argument.
    ctx.obj = {'root_project_dir': root_project_dir,
               'verbose': verbose}

    # Set up application logging. This ensures that only documenteer's
    # logger is activated. If necessary, we can add other app's loggers too.
    if verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logger = logging.getLogger('documenteer')
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(log_level)


@main.command()
@click.argument('topic', default=None, required=False, nargs=1)
@click.pass_context
def help(ctx, topic, **kw):
    """Show help for any command.
    """
    # The help command implementation is taken from
    # https://www.burgundywall.com/post/having-click-help-subcommand
    if topic is None:
        click.echo(ctx.parent.get_help())
    else:
        click.echo(main.commands[topic].get_help(ctx))


@main.command()
@click.option(
    '-s', '--skip', multiple=True,
    help='A module (e.g. ``lsst.afw.geom`` or package (``afw``) name to '
         'exclude from the documentation. Provide multiple -s options to skip '
         'multiple names.'
)
@click.pass_context
def build(ctx, skip):
    """Build documentation as HTML.
    """
    return_code = build_stack_docs(
        ctx.obj['root_project_dir'],
        skippedNames=skip)
    if return_code > 0:
        sys.exit(return_code)


@main.command()
@click.pass_context
def clean(ctx):
    """Clean Sphinx build products.
    """
    logger = logging.getLogger(__name__)

    dirnames = ['py-api', '_build', 'modules', 'packages']
    dirnames = [os.path.join(ctx.obj['root_project_dir'], dirname)
                for dirname in dirnames]
    for dirname in dirnames:
        if os.path.isdir(dirname):
            shutil.rmtree(dirname)
            logger.debug('Cleaned up %r', dirname)
        else:
            logger.debug('Did not clean up %r (missing)', dirname)
