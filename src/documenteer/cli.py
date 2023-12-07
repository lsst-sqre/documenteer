"""Documenteer's command-line interface (CLI)."""

from __future__ import annotations

import click


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(message="%(version)s")
def main() -> None:
    """Documenteer command-line tools.

    You can learn more at https://documenteer.lsst.io/
    """


# display_help is vendored from safir.click.


def display_help(
    main: click.Group,
    ctx: click.Context,
    topic: str | None = None,
    subtopic: str | None = None,
) -> None:
    """Show help for a Click command."""
    if not topic:
        if not ctx.parent:
            raise RuntimeError("help called without topic or parent")
        click.echo(ctx.parent.get_help())
        return
    if topic not in main.commands:
        raise click.UsageError(f"Unknown help topic {topic}", ctx)
    if not subtopic:
        ctx.info_name = topic
        click.echo(main.commands[topic].get_help(ctx))
        return

    # Subtopic handling. This requires some care with typing, since the
    # commands attribute (although present) is not documented, and the
    # get_command method is only available on MultiCommands.
    group = main.commands[topic]
    if isinstance(group, click.MultiCommand):
        command = group.get_command(ctx, subtopic)
        if command:
            ctx.info_name = f"{topic} {subtopic}"
            click.echo(command.get_help(ctx))
            return

    # Fall through to the error case of no subcommand found.
    msg = f"Unknown help topic {topic} {subtopic}"
    raise click.UsageError(msg, ctx)


@main.command()
@click.argument("topic", default=None, required=False, nargs=1)
@click.pass_context
def help(ctx: click.Context, topic: str | None) -> None:
    """Show help for any command."""
    display_help(main, ctx, topic)
