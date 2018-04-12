"""Implements the ``stack-docs`` CLI for stack documentation builds.
"""

__all__ = ('main',)

import click


# Add -h as a help shortcut option
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    '-d', '--dir', 'root_project_dir',
    type=click.Path(exists=True, file_okay=False, dir_okay=True,
                    resolve_path=True),
    default='.',
    help='Root Sphinx project directory'
)
@click.pass_context
def main(ctx, root_project_dir):
    """stack-docs is a CLI for building LSST Stack documentation, such as
    pipelines.lsst.io.
    """
    # Subcommands should use the click.pass_obj decorator to get this
    # ctx.obj object as the first argument.
    ctx.obj = {'root_project_dir': root_project_dir}


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
